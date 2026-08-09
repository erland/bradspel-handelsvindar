# Strategisk simulator – designanalys

## Mål

Simulatorn ska spela hela Handelsvindar med samma begränsningar som en spelare:

- endast kort i den egna handen får betalas
- endast öppna kort och kortlekens topp får dras enligt reglerna
- andra spelares händer är dolda
- byggda rutter och öppna leveranser är synliga
- en upptagen rutt får inte byggas igen
- leveranser kräver ett sammanhängande eget nätverk
- markörer, efterfrågan, poäng och slutrunda hanteras enligt `data/rules.yaml`

## Relevanta strategiprofiler

### Balanserad

Värderar både leveranser, nätverk och kortberedskap. Den fungerar som huvudreferens.

### Leveransfokuserad

Väljer en öppen leverans och söker den billigaste realistiska vägen. Den prioriterar kort och rutter som minskar återstående byggkostnad mot målet.

### Nätverksbyggare

Prioriterar sammanhängande nät, nya anslutna hamnar och rutter som kan återanvändas av flera leveranser.

### Opportunist

Tar färdiga leveranser omedelbart, bygger billiga poängeffektiva rutter och undviker lång förberedelse.

### Blockerare

Värderar centrala rutter och rutter som förekommer i många korta vägar mellan öppna leveranshamnar. Den får inte se motståndarnas händer eller hemlig information.

## Beslutsmodell

Varje tur genererar motorn alla lagliga alternativ:

1. genomförbar leverans
2. byggbar rutt
3. möjliga kortdragningar

Alternativen får ett heuristiskt värde enligt agentens profil. En liten kontrollerad variation gör att identiska agenter inte alltid fattar exakt samma beslut.

## Begränsningar

- Agenten använder viktad kortaste-väg-sökning, inte fullständig spelträdsökning.
- Den antar att öppna leveranser är de viktigaste planeringsmålen.
- Den kan uppskatta blockering men inte läsa motståndarens avsikt säkert.
- Simulationen kan indikera tempo, dominanta profiler, kortbrist och dödlägen.
- Mänskliga tester behövs fortfarande för begriplighet, spänning och spelglädje.
