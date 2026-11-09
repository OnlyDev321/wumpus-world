"""
English / Korean UI text.

Messages are lazy: `T(key, **values)` returns an object that is translated only when it
is turned into a string (when drawn). Switching the language therefore re-translates
everything on screen, including log lines and the agent's reasoning written earlier.
Values may themselves be messages (e.g. a direction) and are translated the same way.
"""

_language = "en"

LANGUAGES = [("en", "EN"), ("ko", "한국어")]


def set_language(code):
    global _language
    _language = code


def get_language():
    return _language


def tr(key, default=None, **values):
    text = STRINGS.get(_language, {}).get(key) or STRINGS["en"].get(key) or default or key
    if values:
        text = text.format(**{k: str(v) for k, v in values.items()})
    return text


class Msg:
    def __init__(self, key, default=None, **values):
        self.key, self.default, self.values = key, default, values

    def __str__(self):
        return tr(self.key, self.default, **self.values)

    def __add__(self, other):
        return Join([self, other], "")


class Join:
    """Several messages shown together, e.g. a list of percepts."""

    def __init__(self, parts, sep=", "):
        self.parts, self.sep = list(parts), sep

    def __str__(self):
        return self.sep.join(str(p) for p in self.parts)

    def __add__(self, other):
        return Join([self, other], "")


def T(key, default=None, **values):
    return Msg(key, default, **values)


def algorithm_label(name):
    return T(f"algo.{name}", default=name)


STRINGS = {
    "en": {
        # Bottom bar
        "group.agent": "Play mode", "group.dungeon": "Dungeon", "group.manual": "Manual control", "group.view": "View",
        "btn.step": "Next step", "mode.auto": "Auto", "mode.step": "Step", "mode.manual": "Manual",
        "speed.slow": "Slow", "speed.normal": "Normal", "speed.fast": "Fast",
        "btn.new_map": "New map", "btn.replay": "Replay", "btn.classic": "Classic", "label.rooms": "Rooms",
        "arrow.ready": "Arrow: 1", "arrow.empty": "No arrows left", "arrow.hint": "Shoot: Shift + ↑←↓→",
        "btn.grab": "Grab gold", "btn.door": "Enter door", "btn.exit": "Exit",
        "sw.reveal": "Reveal map", "sw.dark": "Dark theme", "sw.sound": "Sound", "btn.analytics": "Analytics",
        # Room view
        "room.title": "Room {n}", "room.of": "of {n}",
        "tag.preview": "Preview · click map to return", "tag.entrance": "Entrance", "tag.exit": "Exit",
        "cell.safe": "SAFE", "cell.pit": "PIT", "cell.wumpus": "WUMPUS", "cell.entrance": "ENTRANCE", "cell.exit": "EXIT",
        # Minimap
        "map.title": "Dungeon map", "map.explored": "Explored {a}/{b} cells",
        # Agent panel
        "agent.title": "Agent",
        "status.victory": "Victory", "status.trapped": "Trapped", "status.dead": "Dead", "status.escaped": "Escaped",
        "status.auto": "Auto running", "status.waiting": "Waiting", "status.manual": "Your move",
        "stat.score": "Score", "stat.steps": "Steps", "stat.gold": "Gold", "stat.arrow": "Arrow",
        "gold.found": "Found", "gold.not_yet": "Not yet",
        "label.percepts": "Percepts", "label.reasoning": "Reasoning", "label.log": "Log",
        "percept.breeze": "Breeze", "percept.stench": "Stench", "percept.glitter": "Glitter", "percept.scream": "Scream",
        # Result
        "result.victory.title": "Victory!", "result.victory.desc": "The agent escaped with the gold.",
        "result.pit.title": "Fell into a pit", "result.wumpus.title": "Eaten by the Wumpus",
        "result.learn": "Replay to let the agent learn from it.",
        "result.trapped.title": "Trapped", "result.trapped.desc": "No route left to complete the gold-and-exit goal.",
        "result.escaped.title": "Escaped", "result.escaped.desc": "Left the dungeon without the gold.",
        "result.final": "Final score", "result.hint": "Replay or New map below",
        # Analytics
        "dev.title": "Analytics", "dev.subtitle": "Dev mode · drag to move", "dev.algorithm": "Algorithm",
        "dev.current": "Current game", "dev.outcome": "Outcome", "dev.explored": "Explored",
        "dev.think_avg": "Think avg", "dev.think_max": "Think max", "dev.risky": "Risky moves",
        "dev.doors": "Doors used", "dev.slain": "Wumpus slain", "dev.slain_yes": "Yes",
        "dev.slain_missed": "Missed", "dev.slain_no": "No", "dev.time": "Time",
        "dev.session": "Session", "dev.clear": "Clear", "dev.games": "Games", "dev.win_rate": "Win rate",
        "dev.avg_score": "Avg score", "dev.deaths": "Pit / Wumpus", "dev.avg_steps": "Avg steps",
        "dev.avg_explored": "Avg explored", "dev.kill_rate": "Kill rate",
        "dev.benchmark": "Benchmark · same maps, {n} room(s)", "dev.run": "Run benchmark",
        "dev.running": "Running {algo}: {a}/{b}", "dev.empty": "Pick an algorithm and run {n} games to compare.",
        "col.algorithm": "Algorithm", "col.win": "Win", "col.pit": "Pit", "col.kill": "Kill",
        "col.score": "Score", "col.steps": "Steps", "col.ms": "ms/step",
        "outcome.none": "In progress", "outcome.win": "Victory", "outcome.pit": "Fell into a pit",
        "outcome.wumpus": "Eaten by Wumpus", "outcome.escaped": "Escaped, no gold", "outcome.trapped": "Trapped",
        "algo.Logic + risk": "Logic + risk", "algo.Safe only": "Safe only",
        # Directions
        "dir.UP": "up", "dir.DOWN": "down", "dir.LEFT": "left", "dir.RIGHT": "right",
        # Agent reasoning
        "th.start": "Agent entered the dungeon. Looking for the gold and the exit.",
        "th.replay": "Replay started with episodic memory ({summary}).",
        "mem.pit": "pit at {cells}", "mem.wumpus": "Wumpus at {cell}", "mem.none": "no fatal history",
        "th.to_exit": "Heading to the exit at {exit} via {cell}.",
        "th.grab": "Glitter here! Grabbing the gold.",
        "th.leave_gold": "Gold secured and exit reached. Climbing out!",
        "th.explore": "Safe unvisited cell {target}. Moving to {cell}.",
        "th.risky": "No safe cells left. Taking a calculated risk into {cell} (risk {risk}).",
        "th.avoided": " Memory: avoided {cells}.",
        "th.frontier": "Moving via {cell} towards the lowest-risk cell {target} (risk {risk}, {dist} steps).",
        "th.trapped": "No route left to find the gold or escape with it. The agent is trapped.",
        "th.shoot_sure": "Wumpus located at {where}. Shooting {dir}!",
        "th.shoot_line": "Wumpus is at one of {where}, all in one line. Shooting {dir}!",
        "th.align": "Lining up a shot at the Wumpus ({where}) via {cell}.",
        "th.safe_giveup": "No proven-safe route left to complete the gold-and-exit goal. Giving up.",
        # Log
        "log.entered": "Entered at {cell}: {percepts}", "log.clear": "clear",
        "log.new_dungeon": "New dungeon: {n} room(s).", "log.classic": "Classic map loaded.",
        "log.replay_mem": "Replay (recalled: {summary}).", "log.replay": "Replaying map.",
        "log.algorithm": "Algorithm: {name}.", "log.you": "You: ",
        "log.moved": "{who}Moved to {cell}", "log.room": "Entered Room {n}",
        "log.door": "Went through the door into Room {n}",
        "log.at_door": "Door to Room {n}. Press C to enter.", "log.no_door": "No door here.",
        "log.at_exit": "At the exit. Press C to leave the dungeon.",
        "log.pit": "Fell into a pit at {cell}. Memorized for replay.",
        "log.wumpus": "Eaten by the Wumpus at {cell}. Memorized for replay.",
        "log.grab": "{who}Grabbed the gold (+1000)", "log.no_gold": "No gold here.",
        "log.no_arrows": "No arrows left.",
        "log.hit": "{who}Shot {dir}: Wumpus slain!", "log.miss": "{who}Shot {dir}: missed.",
        "log.win": "{who}Escaped with the gold. Victory!", "log.escaped": "{who}Escaped without the gold.",
        "log.sealed": "The entrance is sealed. Exit is at {cell}.", "log.no_exit": "No exit here. Exit is at {cell}.",
        "log.illegal": "Illegal move to {cell} - the algorithm broke the rules.",
        "log.trapped": "The agent is trapped: no route left to complete the gold-and-exit goal.", "log.wall": "A wall blocks the way.",
    },
    "ko": {
        "group.agent": "플레이 모드", "group.dungeon": "던전", "group.manual": "수동 조작", "group.view": "보기",
        "btn.step": "다음 단계", "mode.auto": "자동", "mode.step": "단계별", "mode.manual": "수동",
        "speed.slow": "느리게", "speed.normal": "보통", "speed.fast": "빠르게",
        "btn.new_map": "새 맵", "btn.replay": "다시 하기", "btn.classic": "클래식", "label.rooms": "방 개수",
        "arrow.ready": "화살: 1", "arrow.empty": "화살 없음", "arrow.hint": "발사: Shift + ↑←↓→",
        "btn.grab": "금괴 줍기", "btn.door": "문 통과", "btn.exit": "탈출",
        "sw.reveal": "전체 맵 보기", "sw.dark": "다크 테마", "sw.sound": "사운드", "btn.analytics": "분석",
        "room.title": "방 {n}", "room.of": "/ {n}",
        "tag.preview": "미리보기 · 지도를 눌러 복귀", "tag.entrance": "입구", "tag.exit": "출구",
        "cell.safe": "안전", "cell.pit": "함정", "cell.wumpus": "웜퍼스", "cell.entrance": "입구", "cell.exit": "출구",
        "map.title": "던전 지도", "map.explored": "탐색 {a}/{b}칸",
        "agent.title": "에이전트",
        "status.victory": "승리", "status.trapped": "고립", "status.dead": "사망", "status.escaped": "탈출",
        "status.auto": "자동 실행 중", "status.waiting": "대기 중", "status.manual": "플레이어 차례",
        "stat.score": "점수", "stat.steps": "걸음", "stat.gold": "금괴", "stat.arrow": "화살",
        "gold.found": "획득", "gold.not_yet": "아직",
        "label.percepts": "감각", "label.reasoning": "추론", "label.log": "로그",
        "percept.breeze": "바람", "percept.stench": "악취", "percept.glitter": "반짝임", "percept.scream": "비명",
        "result.victory.title": "승리!", "result.victory.desc": "에이전트가 금괴를 들고 탈출했습니다.",
        "result.pit.title": "함정에 빠졌습니다", "result.wumpus.title": "웜퍼스에게 잡아먹혔습니다",
        "result.learn": "다시 하기로 이 실패에서 배우게 하세요.",
        "result.trapped.title": "고립되었습니다", "result.trapped.desc": "금괴를 확보해 탈출할 경로를 더 이상 찾을 수 없습니다.",
        "result.escaped.title": "탈출", "result.escaped.desc": "금괴 없이 던전을 나왔습니다.",
        "result.final": "최종 점수", "result.hint": "아래에서 다시 하기 또는 새 맵",
        "dev.title": "분석", "dev.subtitle": "개발자 모드 · 드래그로 이동", "dev.algorithm": "알고리즘",
        "dev.current": "현재 게임", "dev.outcome": "결과", "dev.explored": "탐색",
        "dev.think_avg": "평균 추론 시간", "dev.think_max": "최대 추론 시간", "dev.risky": "위험한 이동",
        "dev.doors": "문 통과", "dev.slain": "웜퍼스 처치", "dev.slain_yes": "예",
        "dev.slain_missed": "빗나감", "dev.slain_no": "아니요", "dev.time": "시간",
        "dev.session": "세션", "dev.clear": "초기화", "dev.games": "게임 수", "dev.win_rate": "승률",
        "dev.avg_score": "평균 점수", "dev.deaths": "함정 / 웜퍼스", "dev.avg_steps": "평균 걸음",
        "dev.avg_explored": "평균 탐색률", "dev.kill_rate": "처치율",
        "dev.benchmark": "벤치마크 · 동일 맵, 방 {n}개", "dev.run": "벤치마크 실행",
        "dev.running": "{algo} 실행 중: {a}/{b}", "dev.empty": "알고리즘을 고르고 {n}게임을 실행해 비교하세요.",
        "col.algorithm": "알고리즘", "col.win": "승리", "col.pit": "함정", "col.kill": "처치",
        "col.score": "점수", "col.steps": "걸음", "col.ms": "ms/결정",
        "outcome.none": "진행 중", "outcome.win": "승리", "outcome.pit": "함정에 빠짐",
        "outcome.wumpus": "웜퍼스에게 잡힘", "outcome.escaped": "금괴 없이 탈출", "outcome.trapped": "고립",
        "algo.Logic + risk": "논리 + 위험 감수", "algo.Safe only": "안전 우선",
        "dir.UP": "위쪽", "dir.DOWN": "아래쪽", "dir.LEFT": "왼쪽", "dir.RIGHT": "오른쪽",
        "th.start": "던전에 들어왔습니다. 금괴와 출구를 찾습니다.",
        "th.replay": "에피소드 기억으로 다시 시작합니다 ({summary}).",
        "mem.pit": "함정: {cells}", "mem.wumpus": "웜퍼스: {cell}", "mem.none": "치명적 기록 없음",
        "th.to_exit": "{cell}을(를) 거쳐 출구 {exit}(으)로 이동합니다.",
        "th.grab": "반짝임 감지! 금괴를 줍습니다.",
        "th.leave_gold": "금괴 확보, 출구 도착. 탈출합니다!",
        "th.explore": "안전한 미방문 칸 {target}. {cell}(으)로 이동합니다.",
        "th.risky": "안전한 칸이 없습니다. {cell}(으)로 계산된 위험을 감수합니다 (위험도 {risk}).",
        "th.avoided": " 기억: {cells} 회피.",
        "th.frontier": "가장 위험이 낮은 칸 {target}을(를) 향해 {cell}(으)로 이동합니다 (위험도 {risk}, {dist}걸음).",
        "th.trapped": "금괴를 찾거나 금괴를 가지고 탈출할 경로가 더 이상 없습니다. 고립되었습니다.",
        "th.shoot_sure": "웜퍼스 위치 {where} 확정. {dir}으로 발사!",
        "th.shoot_line": "웜퍼스는 {where} 중 한 곳, 모두 한 직선 위에 있습니다. {dir}으로 발사!",
        "th.align": "웜퍼스({where})를 조준하기 위해 {cell}(으)로 이동합니다.",
        "th.safe_giveup": "금괴를 확보해 탈출할 안전한 경로가 더 이상 없습니다. 탐색을 중단합니다.",
        "log.entered": "{cell}에서 시작: {percepts}", "log.clear": "감각 없음",
        "log.new_dungeon": "새 던전: 방 {n}개.", "log.classic": "클래식 맵을 불러왔습니다.",
        "log.replay_mem": "다시 하기 (기억: {summary}).", "log.replay": "같은 맵을 다시 시작합니다.",
        "log.algorithm": "알고리즘: {name}.", "log.you": "플레이어: ",
        "log.moved": "{who}{cell}(으)로 이동", "log.room": "방 {n} 진입",
        "log.door": "문을 지나 방 {n}(으)로 이동",
        "log.at_door": "방 {n}(으)로 가는 문입니다. C를 눌러 들어가세요.", "log.no_door": "여기에는 문이 없습니다.",
        "log.at_exit": "출구에 도착했습니다. C를 눌러 탈출하세요.",
        "log.pit": "{cell}에서 함정에 빠졌습니다. 다시 하기를 위해 기억합니다.",
        "log.wumpus": "{cell}에서 웜퍼스에게 잡아먹혔습니다. 다시 하기를 위해 기억합니다.",
        "log.grab": "{who}금괴 획득 (+1000)", "log.no_gold": "여기에는 금괴가 없습니다.",
        "log.no_arrows": "남은 화살이 없습니다.",
        "log.hit": "{who}{dir}으로 발사: 웜퍼스 처치!", "log.miss": "{who}{dir}으로 발사: 빗나감.",
        "log.win": "{who}금괴를 들고 탈출. 승리!", "log.escaped": "{who}금괴 없이 탈출.",
        "log.sealed": "입구는 막혀 있습니다. 출구는 {cell}입니다.",
        "log.no_exit": "여기는 출구가 아닙니다. 출구는 {cell}입니다.",
        "log.illegal": "{cell}(으)로 잘못된 이동 - 알고리즘이 규칙을 어겼습니다.",
        "log.trapped": "에이전트 고립: 금괴를 확보해 탈출할 경로를 더 이상 찾을 수 없습니다.", "log.wall": "벽에 막혔습니다.",
    },
}
