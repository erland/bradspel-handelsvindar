#!/usr/bin/env python3
"""Monte Carlo prototype simulator for Handelsvindar.

Agents choose randomly among legal actions with configurable weights.
Results are hypotheses about tempo and deadlocks, not evidence of fun or final balance.
"""
from pathlib import Path
from collections import Counter, defaultdict, deque
import argparse, copy, json, random, statistics, yaml

ROOT = Path(__file__).resolve().parents[1]

def load(name):
    return yaml.safe_load((ROOT/name).read_text(encoding="utf-8"))

RULES = load("data/rules.yaml")["rules"]
BOARD = load("data/board.yaml")["board"]
CARD_DATA = load("data/cards.yaml")["route_cards"]
DELIVERY_DATA = load("data/deliveries.yaml")["deliveries"]
SIM = load("data/simulation.yaml")["simulation"]

ROUTES = {r["id"]: r for r in BOARD["connections"]}
PORTS = [p["name"] for p in BOARD["ports"]]

def make_deck():
    deck = [c["type"] for c in CARD_DATA for _ in range(int(c.get("count",1)))]
    return deck

def connected(owned_ids, start, goal):
    graph = defaultdict(list)
    for rid in owned_ids:
        r = ROUTES[rid]
        graph[r["from"]].append(r["to"])
        graph[r["to"]].append(r["from"])
    q, seen = deque([start]), {start}
    while q:
        node = q.popleft()
        if node == goal:
            return True
        for nxt in graph[node]:
            if nxt not in seen:
                seen.add(nxt); q.append(nxt)
    return False

def network_size(owned_ids):
    if not owned_ids:
        return 0
    graph = defaultdict(list)
    for rid in owned_ids:
        r=ROUTES[rid]
        graph[r["from"]].append(r["to"]); graph[r["to"]].append(r["from"])
    best=0
    for start in list(graph):
        q=[start]; seen={start}; edges=set()
        while q:
            n=q.pop()
            for nxt in graph[n]:
                edges.add(tuple(sorted((n,nxt))))
                if nxt not in seen:
                    seen.add(nxt); q.append(nxt)
        best=max(best,len(edges))
    return best

def weighted_choice(rng, legal, weights):
    vals=[max(0,float(weights.get(x,1))) for x in legal]
    return rng.choices(legal, weights=vals, k=1)[0]

def play_game(player_count, rng):
    rules=RULES
    route_deck=make_deck(); rng.shuffle(route_deck)
    discard=[]
    open_cards=[]
    for _ in range(rules["setup"]["open_route_card_slots"]):
        if route_deck: open_cards.append(route_deck.pop())
    delivery_deck=copy.deepcopy(DELIVERY_DATA); rng.shuffle(delivery_deck)
    open_deliveries=[delivery_deck.pop() for _ in range(min(rules["setup"]["open_delivery_slots"],len(delivery_deck)))]
    marker_count=rules["setup"]["route_markers_by_player_count"][str(player_count)]
    players=[]
    for _ in range(player_count):
        hand=[]
        for _ in range(rules["setup"]["starting_hand_size"]):
            if route_deck: hand.append(route_deck.pop())
        players.append({"hand":hand,"routes":set(),"score":0,"deliveries":[],"markers":marker_count})
    owned={}
    demand=Counter()
    start_player=rng.randrange(player_count)
    current=start_player
    turns=0; final_turns=None; trigger_player=None
    max_turns=SIM["max_turns_per_game"]
    weights=SIM["agent"]["action_weights"]

    def refill_cards():
        nonlocal route_deck, discard, open_cards
        while len(open_cards)<rules["setup"]["open_route_card_slots"]:
            if not route_deck:
                if not discard: break
                route_deck=discard[:]; discard.clear(); rng.shuffle(route_deck)
            open_cards.append(route_deck.pop())

    def affordable(p):
        result=[]
        counts=Counter(p["hand"]); wild=rules["build_route"]["wild_card_type"]
        for rid,r in ROUTES.items():
            if rid in owned or p["markers"]<r["cost"]: continue
            matching=counts[r["route_type"]]
            maxwild=min(counts[wild],rules["build_route"]["max_wild_cards_per_build"])
            if matching + maxwild >= r["cost"]:
                result.append(rid)
        return result

    while turns < max_turns:
        p=players[current]
        legal=["draw_route_cards"]
        affordable_routes=affordable(p)
        if affordable_routes: legal.append("build_route")
        completable=[d for d in open_deliveries if connected(p["routes"],d["from"],d["to"])]
        if completable: legal.append("complete_delivery")
        action=weighted_choice(rng,legal,weights)

        if action=="draw_route_cards":
            draws=rules["draw_route_cards"]["normal_draw_count"]
            for _ in range(draws):
                choices=(["open"] if open_cards else [])+(["blind"] if route_deck else [])
                if not choices: break
                source=rng.choice(choices)
                if source=="open":
                    card=rng.choice(open_cards); open_cards.remove(card); p["hand"].append(card); refill_cards()
                    if card==rules["build_route"]["wild_card_type"] and rules["draw_route_cards"]["open_wild_card_ends_action"]:
                        break
                else:
                    p["hand"].append(route_deck.pop())
        elif action=="build_route":
            rid=rng.choice(affordable_routes); route=ROUTES[rid]; need=route["cost"]
            matching=route["route_type"]; wild=rules["build_route"]["wild_card_type"]
            use_match=min(need,p["hand"].count(matching))
            for _ in range(use_match): p["hand"].remove(matching); discard.append(matching)
            remaining=need-use_match
            for _ in range(remaining): p["hand"].remove(wild); discard.append(wild)
            p["routes"].add(rid); owned[rid]=current; p["markers"]-=need
            p["score"]+=rules["build_route"]["build_points_by_cost"][str(need)]
        else:
            d=rng.choice(completable); open_deliveries.remove(d); p["deliveries"].append(d["id"])
            dest=d["to"]; modifier=rules["demand"]["first_delivery_bonus"] if demand[dest]==0 else (rules["demand"]["second_delivery_modifier"] if demand[dest]==1 else rules["demand"]["third_or_later_penalty"])
            p["score"]+=d["points"]+modifier; demand[dest]+=rules["demand"]["increment_after_delivery"]
            if delivery_deck: open_deliveries.append(delivery_deck.pop())

        turns+=1
        if final_turns is None and p["markers"]<=rules["end_game"]["trigger_when_route_markers_at_or_below"]:
            trigger_player=current
            final_turns=player_count+1
        if final_turns is not None:
            final_turns-=1
            if final_turns<=0: break
        current=(current+1)%player_count

    # Largest network bonus.
    sizes=[network_size(p["routes"]) for p in players]
    best=max(sizes)
    if sizes.count(best)==1 and best>0:
        players[sizes.index(best)]["score"]+=rules["final_scoring"]["largest_connected_network_bonus"]

    used_ports=set()
    for p in players:
        for rid in p["routes"]:
            used_ports.add(ROUTES[rid]["from"]); used_ports.add(ROUTES[rid]["to"])
    return {
        "turns":turns,
        "rounds":turns/player_count,
        "scores":[p["score"] for p in players],
        "completed_deliveries":[len(p["deliveries"]) for p in players],
        "built_routes":[len(p["routes"]) for p in players],
        "unused_ports":len(set(PORTS)-used_ports),
        "end_triggered":trigger_player is not None,
        "stalemate":turns>=max_turns,
    }

def summarize(results):
    flat_scores=[s for r in results for s in r["scores"]]
    return {
        "games":len(results),
        "mean_turns":round(statistics.mean(r["turns"] for r in results),2),
        "mean_rounds":round(statistics.mean(r["rounds"] for r in results),2),
        "mean_score_per_player":round(statistics.mean(flat_scores),2),
        "mean_deliveries_per_player":round(statistics.mean(x for r in results for x in r["completed_deliveries"]),2),
        "mean_routes_per_player":round(statistics.mean(x for r in results for x in r["built_routes"]),2),
        "mean_unused_ports":round(statistics.mean(r["unused_ports"] for r in results),2),
        "end_trigger_rate":round(sum(r["end_triggered"] for r in results)/len(results),3),
        "stalemate_rate":round(sum(r["stalemate"] for r in results)/len(results),3),
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--games",type=int,default=SIM["games"])
    ap.add_argument("--players",type=int,choices=[2,3,4])
    ap.add_argument("--seed",type=int,default=SIM["seed"])
    ap.add_argument("--output",default=str(ROOT/"output"/"simulation-summary.json"))
    args=ap.parse_args()
    rng=random.Random(args.seed)
    counts=[args.players] if args.players else SIM["player_counts"]
    report={"rules_version":RULES["version"],"agent":SIM["agent"],"warning":SIM["interpretation"],"by_player_count":{}}
    for pc in counts:
        results=[play_game(pc,rng) for _ in range(args.games)]
        report["by_player_count"][str(pc)]=summarize(results)
    Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    Path(args.output).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
