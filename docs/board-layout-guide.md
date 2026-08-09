# Kartlayout v0.8

Speldata och visuell layout är separerade.

- `data/board.yaml` innehåller hamnar och rutter.
- `data/board-layout.yaml` innehåller koordinater, etikettförskjutningar, kurvning och kostnadspositioner.
- `tools/board-layout-editor.html` är en lokal editor för att dra hamnar och exportera koordinater.
- `scripts/check_board_layout.py` gör en enkel kontroll av etikettkollisioner.

## Kurvor

`curve_mm: 0` ger rak linje. Positivt och negativt värde böjer rutten åt var sitt håll.

## Kostnadscirkel

`cost_t` anger position längs rutten från 0 till 1. `cost_normal_mm` flyttar cirkeln vinkelrätt från rutten.

## Etiketter

`label_dx_mm` och `label_dy_mm` flyttar ortsnamnet utan att flytta hamnen.
