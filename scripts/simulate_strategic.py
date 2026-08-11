#!/usr/bin/env python3
"""Strategic, rules-constrained simulator for Handelsvindar v0.30."""
from __future__ import annotations
from pathlib import Path
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
import argparse, copy, heapq, itertools, json, math, random, statistics, yaml

ROOT = Path(__file__).resolve().parents[1]

def load_yaml(path):
    return yaml.safe_load((ROOT/path).read_text(encoding="utf-8"))

RULES = load_yaml("data/rules.yaml")["rules"]
BOARD = load_yaml("data/board.yaml")["board"]
CARDS = load_yaml("data/cards.yaml")["route_cards"]
DELIVERIES = load_yaml("data/deliveries.yaml")["deliveries"]
CONFIG = load_yaml("data/strategies.yaml")["strategic_simulation"]

ROUTES = {r["id"]: r for r in BOARD["connections"]}
PORTS = [p["name"] for p in BOARD["ports"]]
INCIDENT = defaultdict(list)
for rid, r in ROUTES.items():
    INCIDENT[r["from"]].append((r["to"], rid))
    INCIDENT[r["to"]].append((r["from"], rid))

def make_deck():
    return [c["type"] for c in CARDS for _ in range(int(c.get("count", 1)))]

def owned_graph(route_ids):
    g = defaultdict(list)
    for rid in route_ids:
        r = ROUTES[rid]
        g[r["from"]].append(r["to"])
        g[r["to"]].append(r["from"])
    return g

def connected(route_ids, start, goal):
    if start == goal:
        return True
    g = owned_graph(route_ids)
    q, seen = deque([start]), {start}
    while q:
        node = q.popleft()
        for nxt in g[node]:
            if nxt == goal:
                return True
            if nxt not in seen:
                seen.add(nxt)
                q.append(nxt)
    return False

def component_ports(route_ids):
    g = owned_graph(route_ids)
    seen, comps = set(), []
    for start in g:
        if start in seen:
            continue
        q=[start]; seen.add(start); nodes=set()
        while q:
            n=q.pop(); nodes.add(n)
            for nxt in g[n]:
                if nxt not in seen:
                    seen.add(nxt); q.append(nxt)
        comps.append(nodes)
    return comps

def largest_network_edges(route_ids):
    if not route_ids:
        return 0
    comps = component_ports(route_ids)
    best = 0
    for nodes in comps:
        edges = sum(1 for rid in route_ids if ROUTES[rid]["from"] in nodes and ROUTES[rid]["to"] in nodes)
        best = max(best, edges)
    return best

def route_centrality(open_deliveries, owned):
    """Count route appearances in several cheapest unblocked paths for open goals."""
    score = Counter()
    for d in open_deliveries:
        paths = k_shortest_candidate_paths(d["from"], d["to"], owned, k=3)
        for rank, path in enumerate(paths):
            weight = 1.0/(rank+1)
            for rid in path:
                score[rid] += weight
    return score

def k_shortest_candidate_paths(start, goal, owned, k=3):
    # Small graph: enumerate simple paths with a bounded heap.
    heap=[(0, start, tuple(), frozenset([start]))]
    found=[]
    while heap and len(found)<k:
        cost,node,path,seen=heapq.heappop(heap)
        if node==goal:
            found.append(list(path)); continue
        for nxt,rid in INCIDENT[node]:
            if nxt in seen or rid in owned:
                continue
            edge=ROUTES[rid]
            heapq.heappush(heap,(cost+edge["cost"],nxt,path+(rid,),seen|{nxt}))
    return found

def missing_cards_for_route(hand, route):
    wild = RULES["build_route"]["wild_card_type"]
    need = route["cost"]
    matching = hand.count(route["route_type"])
    wilds = min(hand.count(wild), RULES["build_route"]["max_wild_cards_per_build"])
    return max(0, need - matching - wilds)

def can_afford(hand, route):
    return missing_cards_for_route(hand, route) == 0

def pay_route(hand, route, discard):
    wild = RULES["build_route"]["wild_card_type"]
    need = route["cost"]
    use_matching = min(need, hand.count(route["route_type"]))
    for _ in range(use_matching):
        hand.remove(route["route_type"]); discard.append(route["route_type"])
    for _ in range(need-use_matching):
        if wild not in hand:
            raise AssertionError("illegal payment")
        hand.remove(wild); discard.append(wild)

def weighted_shortest_plan(player, delivery, owned):
    """Dijkstra using owned routes as zero and unowned legal routes by card burden."""
    hand=player["hand"]
    heap=[(0.0, delivery["from"], tuple())]
    best={delivery["from"]:0.0}
    while heap:
        cost,node,path=heapq.heappop(heap)
        if node==delivery["to"]:
            return list(path), cost
        if cost>best.get(node,1e9):
            continue
        for nxt,rid in INCIDENT[node]:
            if rid in owned and owned[rid] != player["seat"]:
                continue
            r=ROUTES[rid]
            if rid in player["routes"]:
                edge_cost=0.05
            else:
                missing=missing_cards_for_route(hand,r)
                edge_cost=r["cost"] + 1.7*missing
            nc=cost+edge_cost
            if nc<best.get(nxt,1e9):
                best[nxt]=nc
                heapq.heappush(heap,(nc,nxt,path+(rid,)))
    return [], float("inf")

def delivery_value(player, delivery, demand):
    mod = RULES["demand"]["first_delivery_bonus"] if demand[delivery["to"]]==0 else (
        RULES["demand"]["second_delivery_modifier"] if demand[delivery["to"]]==1
        else RULES["demand"]["third_or_later_penalty"]
    )
    return delivery["points"] + mod

@dataclass
class Agent:
    profile: str
    weights: dict
    rng: random.Random

    def noise(self):
        return self.rng.uniform(-0.18, 0.18)

    def choose_target(self, state, player):
        candidates=[]
        for d in state["open_deliveries"]:
            path,cost=weighted_shortest_plan(player,d,state["owned"])
            if not path and not connected(player["routes"],d["from"],d["to"]):
                continue
            value=delivery_value(player,d,state["demand"])
            reusable=sum(1 for rid in path if any(
                rid in weighted_shortest_plan(player, other, state["owned"])[0]
                for other in state["open_deliveries"] if other["id"] != d["id"]
            ))
            utility=value*1.3 - cost + reusable*0.7
            candidates.append((utility,d,path,cost))
        return max(candidates,key=lambda x:x[0],default=None)

    def score_delivery(self, state, player, delivery):
        w=self.weights
        value=delivery_value(player,delivery,state["demand"])
        return w["immediate_delivery"]*value + self.noise()

    def score_route(self, state, player, rid, target, centrality):
        r=ROUTES[rid]; w=self.weights
        build_points=RULES["build_route"]["build_points_by_cost"][str(r["cost"])]
        before_ports=set().union(*component_ports(player["routes"])) if player["routes"] else set()
        after_routes=set(player["routes"])|{rid}
        after_ports=set().union(*component_ports(after_routes)) if after_routes else set()
        new_ports=len(after_ports-before_ports)
        joins_components=max(0,len(component_ports(player["routes"]))-len(component_ports(after_routes)))
        network_growth=new_ports+1.5*joins_components
        progress=0.0
        if target:
            _,d,path,_=target
            if rid in path:
                progress=2.5 + r["cost"]*0.5
        efficiency=build_points/max(1,r["cost"])
        flexibility=len(INCIDENT[r["from"]])+len(INCIDENT[r["to"]])
        block=centrality.get(rid,0.0)
        markers_after=player["markers"]-r["cost"]
        endgame=1.0 if markers_after<=RULES["end_game"]["trigger_when_route_markers_at_or_below"] else 0.0
        return (
            w["route_points"]*build_points +
            w["delivery_progress"]*progress +
            w["network_growth"]*network_growth +
            w["blocking"]*block +
            w["card_efficiency"]*efficiency +
            w["future_flexibility"]*(flexibility/6.0) +
            w["endgame"]*endgame +
            self.noise()
        )

    def desired_types(self, state, player, target):
        needs=Counter()
        if target:
            _,_,path,_=target
            for rid in path:
                if rid in player["routes"] or rid in state["owned"]:
                    continue
                r=ROUTES[rid]
                needs[r["route_type"]] += missing_cards_for_route(player["hand"],r)
        # Network builders value types available near their current network.
        if self.profile=="network_builder":
            connected_ports=set().union(*component_ports(player["routes"])) if player["routes"] else set(PORTS)
            for rid,r in ROUTES.items():
                if rid in state["owned"]: continue
                if r["from"] in connected_ports or r["to"] in connected_ports:
                    needs[r["route_type"]] += 0.3
        return needs

    def choose_card_source(self, state, player, target, draw_index):
        desired=self.desired_types(state,player,target)
        wild=RULES["build_route"]["wild_card_type"]
        options=[]
        for idx,card in enumerate(state["open_cards"]):
            val=desired.get(card,0.0)*3.0 + (4.0 if card==wild else 0.0)
            if card==wild and draw_index>0:
                # Taking an open wild after another card is illegal.
                continue
            options.append((val+self.noise(),"open",idx,card))
        if state["route_deck"]:
            blind_expectation=1.0 + 0.15*sum(desired.values())
            options.append((blind_expectation+self.noise(),"blind",None,None))
        return max(options,key=lambda x:x[0]) if options else None

    def choose_action(self, state, player):
        target=self.choose_target(state,player)
        centrality=route_centrality(state["open_deliveries"],state["owned"])
        candidates=[]
        for d in state["open_deliveries"]:
            if connected(player["routes"],d["from"],d["to"]):
                candidates.append((self.score_delivery(state,player,d),"delivery",d))
        for rid,r in ROUTES.items():
            if rid in state["owned"] or player["markers"]<r["cost"]:
                continue
            if can_afford(player["hand"],r):
                candidates.append((self.score_route(state,player,rid,target,centrality),"build",rid))
        # Drawing is valued by how much the target still needs and by low hand size.
        desired=self.desired_types(state,player,target)
        draw_value=3.0 + 1.6*sum(desired.values()) + max(0,5-len(player["hand"]))*0.6 + self.noise()
        candidates.append((draw_value,"draw",None))
        return max(candidates,key=lambda x:x[0])

def refill_open_cards(state, rng):
    slots=RULES["setup"]["open_route_card_slots"]
    while len(state["open_cards"])<slots:
        if not state["route_deck"]:
            if not state["discard"]:
                break
            state["route_deck"]=state["discard"][:]
            state["discard"].clear()
            rng.shuffle(state["route_deck"])
        state["open_cards"].append(state["route_deck"].pop())

def execute_draw(state, player, agent, target):
    draw_count=RULES["draw_route_cards"]["normal_draw_count"]
    drawn=[]
    for i in range(draw_count):
        choice=agent.choose_card_source(state,player,target,i)
        if not choice: break
        _,source,idx,card=choice
        if source=="open":
            card=state["open_cards"].pop(idx)
            player["hand"].append(card); drawn.append(card)
            refill_open_cards(state,agent.rng)
            if card == RULES["build_route"]["wild_card_type"] and RULES["draw_route_cards"]["open_wild_card_ends_action"]:
                break
        else:
            card=state["route_deck"].pop()
            player["hand"].append(card); drawn.append(card)
    return drawn

def new_game(player_count, profiles, rng):
    deck=make_deck(); rng.shuffle(deck)
    open_cards=[deck.pop() for _ in range(min(RULES["setup"]["open_route_card_slots"],len(deck)))]
    delivery_deck=copy.deepcopy(DELIVERIES); rng.shuffle(delivery_deck)
    open_deliveries=[delivery_deck.pop() for _ in range(min(RULES["setup"]["open_delivery_slots"],len(delivery_deck)))]
    markers=RULES["setup"]["route_markers_by_player_count"][str(player_count)]
    players=[]
    for seat,profile in enumerate(profiles):
        hand=[deck.pop() for _ in range(min(RULES["setup"]["starting_hand_size"],len(deck)))]
        players.append({"seat":seat,"profile":profile,"hand":hand,"routes":set(),"score":0,"deliveries":[],"markers":markers})
    return {
        "players":players,"route_deck":deck,"discard":[],"open_cards":open_cards,
        "delivery_deck":delivery_deck,"open_deliveries":open_deliveries,
        "owned":{},"demand":Counter(),"turns":0,"illegal_actions":0
    }

def play_game(player_count, profiles, rng):
    state=new_game(player_count,profiles,rng)
    agents=[Agent(p,CONFIG["profiles"][p]["weights"],random.Random(rng.randrange(10**9))) for p in profiles]
    current=rng.randrange(player_count)
    final_turns=None
    max_turns=CONFIG["max_turns_per_game"]
    action_counts=Counter()
    while state["turns"]<max_turns:
        player=state["players"][current]; agent=agents[current]
        target=agent.choose_target(state,player)
        _,action,payload=agent.choose_action(state,player)
        action_counts[(player["profile"],action)]+=1
        if action=="delivery":
            d=payload
            assert d in state["open_deliveries"]
            assert connected(player["routes"],d["from"],d["to"])
            state["open_deliveries"].remove(d)
            mod=RULES["demand"]["first_delivery_bonus"] if state["demand"][d["to"]]==0 else (
                RULES["demand"]["second_delivery_modifier"] if state["demand"][d["to"]]==1
                else RULES["demand"]["third_or_later_penalty"])
            player["score"]+=d["points"]+mod
            player["deliveries"].append(d["id"])
            state["demand"][d["to"]]+=RULES["demand"]["increment_after_delivery"]
            if state["delivery_deck"]:
                state["open_deliveries"].append(state["delivery_deck"].pop())
        elif action=="build":
            rid=payload; r=ROUTES[rid]
            assert rid not in state["owned"]
            assert player["markers"]>=r["cost"]
            assert can_afford(player["hand"],r)
            pay_route(player["hand"],r,state["discard"])
            player["routes"].add(rid); state["owned"][rid]=current
            player["markers"]-=r["cost"]
            player["score"]+=RULES["build_route"]["build_points_by_cost"][str(r["cost"])]
        else:
            execute_draw(state,player,agent,target)
        state["turns"]+=1
        if final_turns is None and player["markers"]<=RULES["end_game"]["trigger_when_route_markers_at_or_below"]:
            final_turns=player_count+1
        if final_turns is not None:
            final_turns-=1
            if final_turns<=0:
                break
        current=(current+1)%player_count

    sizes=[largest_network_edges(p["routes"]) for p in state["players"]]
    if sizes and sizes.count(max(sizes))==1 and max(sizes)>0:
        state["players"][sizes.index(max(sizes))]["score"]+=RULES["final_scoring"]["largest_connected_network_bonus"]
    scores=[p["score"] for p in state["players"]]
    best=max(scores)
    winners=[i for i,s in enumerate(scores) if s==best]
    if len(winners)>1:
        maxdel=max(len(state["players"][i]["deliveries"]) for i in winners)
        winners=[i for i in winners if len(state["players"][i]["deliveries"])==maxdel]
    return {
        "turns":state["turns"],"rounds":state["turns"]/player_count,
        "players":[{
            "profile":p["profile"],"score":p["score"],"deliveries":len(p["deliveries"]),
            "routes":len(p["routes"]),"markers":p["markers"],"hand_size":len(p["hand"]),
            "owned_route_ids": sorted(p["routes"]),
            "won":i in winners
        } for i,p in enumerate(state["players"])],
        "stalemate":state["turns"]>=max_turns,
        "illegal_actions":state["illegal_actions"],
        "action_counts":{f"{k[0]}:{k[1]}":v for k,v in action_counts.items()}
    }

def profile_lineups(player_count):
    names=list(CONFIG["profiles"])
    if player_count==2:
        return list(itertools.combinations(names,2))
    if player_count==3:
        return list(itertools.combinations(names,3))
    # Representative four-player tables, including each profile in multiple contexts.
    return [
        ("balanced","delivery_focused","network_builder","opportunist"),
        ("balanced","delivery_focused","network_builder","blocker"),
        ("balanced","delivery_focused","opportunist","blocker"),
        ("balanced","network_builder","opportunist","blocker"),
        ("delivery_focused","network_builder","opportunist","blocker"),
    ]

def summarize(games):
    profile_rows=defaultdict(lambda:{
        "games":0,"wins":0.0,"scores":[],"deliveries":[],"routes":[],
        "route_counts":Counter()
    })
    overall_route_counts=Counter()
    head_to_head=defaultdict(lambda:{"games":0,"wins":0.0})
    for g in games:
        profiles_at_table=[p["profile"] for p in g["players"]]
        for p in g["players"]:
            row=profile_rows[p["profile"]]
            row["games"]+=1
            row["wins"]+=1.0 if p["won"] else 0.0
            row["scores"].append(p["score"])
            row["deliveries"].append(p["deliveries"])
            row["routes"].append(p["routes"])
            row["route_counts"].update(p["owned_route_ids"])
            overall_route_counts.update(p["owned_route_ids"])
            for opp in profiles_at_table:
                if opp==p["profile"]:
                    continue
                key=(p["profile"],opp)
                head_to_head[key]["games"]+=1
                head_to_head[key]["wins"]+=1.0 if p["won"] else 0.0

    profiles={}
    for name,row in profile_rows.items():
        total_games=max(1,row["games"])
        profiles[name]={
            "games":row["games"],
            "win_rate":round(row["wins"]/total_games,3),
            "mean_score":round(statistics.mean(row["scores"]),2),
            "mean_deliveries":round(statistics.mean(row["deliveries"]),2),
            "mean_routes":round(statistics.mean(row["routes"]),2),
            "top_routes":[
                {"route_id":rid,"claim_rate":round(cnt/total_games,3)}
                for rid,cnt in row["route_counts"].most_common(8)
            ]
        }

    route_stats=[]
    for rid,count in overall_route_counts.items():
        r=ROUTES[rid]
        route_stats.append({
            "route_id":rid,
            "from":r["from"],
            "to":r["to"],
            "route_type":r["route_type"],
            "cost":r["cost"],
            "claim_rate":round(count/len(games),3)
        })
    route_stats.sort(key=lambda x:x["claim_rate"], reverse=True)

    h2h={}
    for (a,b),row in head_to_head.items():
        h2h[f"{a}_vs_{b}"]={
            "games":row["games"],
            "win_rate":round(row["wins"]/max(1,row["games"]),3)
        }

    return {
        "games":len(games),
        "mean_turns":round(statistics.mean(g["turns"] for g in games),2),
        "mean_rounds":round(statistics.mean(g["rounds"] for g in games),2),
        "stalemate_rate":round(sum(g["stalemate"] for g in games)/len(games),3),
        "illegal_action_count":sum(g["illegal_actions"] for g in games),
        "profiles":profiles,
        "routes_most_claimed":route_stats[:12],
        "routes_least_claimed":sorted(route_stats,key=lambda x:x["claim_rate"])[:12],
        "head_to_head":h2h
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--games-per-lineup",type=int,default=CONFIG["games_per_matchup"])
    ap.add_argument("--players",type=int,choices=[2,3,4])
    ap.add_argument("--seed",type=int,default=CONFIG["seed"])
    ap.add_argument("--output",default=str(ROOT/"output"/"strategic-simulation-summary.json"))
    args=ap.parse_args()
    rng=random.Random(args.seed)
    counts=[args.players] if args.players else CONFIG["player_counts"]
    report={
        "version":(ROOT/"VERSION").read_text(encoding="utf-8").strip(),
        "warning":CONFIG["interpretation"],
        "engine_constraints":{
            "uses_actual_hands":True,"uses_open_market":True,"opponent_hands_hidden":True,
            "exclusive_routes":True,"marker_limits":True,"delivery_connectivity_required":True,
            "demand_and_endgame_rules":True
        },
        "by_player_count":{}
    }
    for pc in counts:
        games=[]
        for lineup in profile_lineups(pc):
            for _ in range(args.games_per_lineup):
                seats=list(lineup)
                rng.shuffle(seats)
                games.append(play_game(pc,seats,rng))
        report["by_player_count"][str(pc)]=summarize(games)
    out=Path(args.output); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
