# Graph Report - wumpus-world  (2026-11-11)

## Corpus Check
- 21 files · ~18,349 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: .otf 3, (none) 2)

## Summary
- 369 nodes · 763 edges · 13 communities (7 shown, 6 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 49 edges (avg confidence: 0.88)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9a086bc0`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- main.py
- main
- Agent
- Board
- GameManager
- World
- Renderer
- Painter
- 🧠 Agentic Wumpus World
- board.py
- SoundManager
- CLAUDE.md
- .claude/CLAUDE.md

## God Nodes (most connected - your core abstractions)
1. `GameManager` - 39 edges
2. `T()` - 30 edges
3. `World` - 27 edges
4. `Board` - 25 edges
5. `Painter` - 25 edges
6. `main()` - 24 edges
7. `Agent` - 23 edges
8. `Renderer` - 23 edges
9. `DevPanel` - 22 edges
10. `ControlPanel` - 17 edges

## Surprising Connections (you probably didn't know these)
- `📊 Dev mode (Analytics)` --references--> `Agent`  [INFERRED]
  README.md → game/agent.py
- `Board` --uses--> `Painter`  [INFERRED]
  board.py → ui/painter.py
- `ControlPanel` --uses--> `World`  [INFERRED]
  ui/controls.py → game/world.py
- `main()` --calls--> `Agent`  [EXTRACTED]
  main.py → game/agent.py
- `DevPanel` --uses--> `Benchmark`  [INFERRED]
  ui/dev_panel.py → game/benchmark.py

## Import Cycles
- None detected.

## Communities (13 total, 6 thin omitted)

### Community 0 - "main.py"
Cohesion: 0.07
Nodes (10): get_language(), set_language(), handle_key(), ControlPanel, _hotkey(), Button, Segmented, Stepper (+2 more)

### Community 1 - "main"
Cohesion: 0.06
Nodes (8): algorithm_name(), Benchmark, main(), play_one(), summarize(), algorithm_label(), main(), DevPanel

### Community 2 - "Agent"
Cohesion: 0.07
Nodes (5): Agent, SafeOnlyAgent, Join, calculate_cell_risk(), deduce_knowledge()

### Community 3 - "Board"
Cohesion: 0.12
Nodes (3): Board, main(), Sprites

### Community 6 - "Renderer"
Cohesion: 0.13
Nodes (3): Msg, tr(), Renderer

### Community 8 - "🧠 Agentic Wumpus World"
Cohesion: 0.09
Nodes (21): 1. 명제 논리 지식 베이스 (Knowledge Base), 1. 저장소 클론 (Clone Repository), 1. 환경 지각 신호 (Percepts) & 객체, 2. 가상환경 생성 및 활성화, 2. 점수 규칙 (Scoring System), 2. 행동 우선순위 (Decision Hierarchy), 3. 🧠 에피소드 사망 기억 및 적응 학습 (Episodic Memory & Failure Learning), 3. 패키지 설치 (+13 more)

### Community 9 - "board.py"
Cohesion: 0.18
Nodes (3): create_window(), create_window(), asset()

## Knowledge Gaps
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `main()` connect `main` to `main.py`, `Agent`, `GameManager`, `World`, `Renderer`, `board.py`, `SoundManager`?**
  _High betweenness centrality (0.236) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `GameManager` (e.g. with `Join` and `World`) actually correct?**
  _`GameManager` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Should `main.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07058001397624039 - nodes in this community are weakly interconnected._
- **Why does `Agent` connect `Agent` to `main.py`, `main`, `🧠 Agentic Wumpus World`?**
  _High betweenness centrality (0.218) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `World` (e.g. with `GameManager` and `ControlPanel`) actually correct?**
  _`World` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Should `main` be split into smaller, more focused modules?**
  _Cohesion score 0.06448979591836734 - nodes in this community are weakly interconnected._
- **Why does `World` connect `World` to `main.py`, `main`, `GameManager`?**
  _High betweenness centrality (0.182) - this node is a cross-community bridge._