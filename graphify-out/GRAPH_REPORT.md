# Graph Report - wumpus-world  (2026-11-12)

## Corpus Check
- 22 files · ~19,068 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: .otf 3, (none) 2)

## Summary
- 379 nodes · 781 edges · 14 communities (9 shown, 5 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 42 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `6aa2dcfa`
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
- benchmark.py

## God Nodes (most connected - your core abstractions)
1. `GameManager` - 38 edges
2. `T()` - 31 edges
3. `Agent` - 27 edges
4. `World` - 26 edges
5. `Board` - 25 edges
6. `Painter` - 24 edges
7. `main()` - 24 edges
8. `Renderer` - 23 edges
9. `DevPanel` - 22 edges
10. `tr()` - 14 edges

## Surprising Connections (you probably didn't know these)
- `📊 Dev mode (Analytics)` --references--> `Agent`  [INFERRED]
  README.md → game/agent.py
- `ControlPanel` --uses--> `World`  [INFERRED]
  ui/controls.py → game/world.py
- `DevPanel` --uses--> `Benchmark`  [INFERRED]
  ui/dev_panel.py → game/benchmark.py
- `Board` --uses--> `Painter`  [INFERRED]
  board.py → ui/painter.py
- `main()` --calls--> `GameManager`  [EXTRACTED]
  main.py → game/game_manager.py

## Import Cycles
- None detected.

## Communities (14 total, 5 thin omitted)

### Community 0 - "main.py"
Cohesion: 0.07
Nodes (11): algorithm_name(), algorithm_label(), get_language(), set_language(), handle_key(), _hotkey(), Button, Segmented (+3 more)

### Community 1 - "main"
Cohesion: 0.09
Nodes (3): main(), ControlPanel, DevPanel

### Community 2 - "Agent"
Cohesion: 0.06
Nodes (5): Agent, SafeOnlyAgent, Join, calculate_cell_risk(), deduce_knowledge()

### Community 3 - "Board"
Cohesion: 0.12
Nodes (3): Board, main(), Sprites

### Community 4 - "GameManager"
Cohesion: 0.14
Nodes (3): play_one(), GameManager, T()

### Community 6 - "Renderer"
Cohesion: 0.13
Nodes (3): Msg, tr(), Renderer

### Community 8 - "🧠 Agentic Wumpus World"
Cohesion: 0.09
Nodes (21): 1. 명제 논리 지식 베이스 (Knowledge Base), 1. 저장소 클론 (Clone Repository), 1. 환경 지각 신호 (Percepts) & 객체, 2. 가상환경 생성 및 활성화, 2. 점수 규칙 (Scoring System), 2. 행동 우선순위 (Decision Hierarchy), 3. 🧠 에피소드 사망 기억 및 적응 학습 (Episodic Memory & Failure Learning), 3. 패키지 설치 (+13 more)

### Community 9 - "board.py"
Cohesion: 0.18
Nodes (3): create_window(), create_window(), asset()

### Community 13 - "benchmark.py"
Cohesion: 0.19
Nodes (3): Benchmark, main(), summarize()

## Knowledge Gaps
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Agent` connect `Agent` to `main.py`, `main`, `🧠 Agentic Wumpus World`?**
  _High betweenness centrality (0.239) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `Agent` (e.g. with `Join` and `📊 Dev mode (Analytics)`) actually correct?**
  _`Agent` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Should `main.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07077922077922078 - nodes in this community are weakly interconnected._
- **Why does `main()` connect `main` to `main.py`, `Agent`, `GameManager`, `World`, `Renderer`, `board.py`, `SoundManager`, `benchmark.py`?**
  _High betweenness centrality (0.209) - this node is a cross-community bridge._
- **Should `main` be split into smaller, more focused modules?**
  _Cohesion score 0.0907258064516129 - nodes in this community are weakly interconnected._
- **Why does `World` connect `World` to `main.py`, `main`, `GameManager`, `benchmark.py`?**
  _High betweenness centrality (0.174) - this node is a cross-community bridge._
- **Should `Agent` be split into smaller, more focused modules?**
  _Cohesion score 0.06290471785383904 - nodes in this community are weakly interconnected._