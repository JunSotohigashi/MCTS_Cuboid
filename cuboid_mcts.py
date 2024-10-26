"""cuboid_mctsモジュール
mctsによるcuboidの手決定を行う.
"""

import random
from cuboid_manager import Board, Move
from cuboid_gamestate import GameState

N_CHILD = 4
EXPAND_THRESHOLD = 9
PLAYOUT_STOP = 30


class UCT_MCTS:
    """UCT-MCTSにより最適な次の指し手を決定する."""

    def __init__(self) -> None:
        """オブジェクトを初期化する."""
        self.__state_now: GameState = GameState()
        self.__state_in_process: GameState = self.__state_now
        self.state_root: GameState = self.__state_now
        self.__expand()

    def get_board(self) -> Board:
        """現在のノードに対応するBoordを返す.

        Returns:
            Board: Boardデータ
        """
        return self.__state_now.board

    def decide(self) -> int:
        """次のMoveを決定する.
        子ノードのうち, 試行回数が最大のインデックスを返す.
        最大が複数ある場合は, その中からランダムに選択する.

        Returns:
            int: 決定された子のインデックス
        """
        self.__state_in_process: GameState = self.__state_now
        p = self.__state_now.get_children()[0].move_data.player
        # n_list = [c.playout_result[0] for c in self.__state_now.get_children()]   # 試行回数 最大
        n_list = [c.playout_result[0]+c.playout_result[p+1]-c.playout_result[((p+1)%2)+1] for c in self.__state_now.get_children()]   # 試行回数+勝ち-負け 最大
        # n_list = [c.playout_result[0]+c.playout_result[1]+c.playout_result[2] for c in self.__state_now.get_children()]   # 試行回数+勝ち+負け 最大
        v_list = [c.move_data.value for c in self.__state_now.get_children()]
        v_max = max(v_list)
        decided_i = None
        if v_max >= 10000:
            n_max = max([n for n,v in zip(n_list,v_list) if v >= 10000])
            decided_i = random.choice([i for i,(n,v) in enumerate(zip(n_list, v_list)) if v >= 10000 and n == n_max])
        else:
            n_max = max(n_list)
            if n_list.count(n_max) == 1:
                decided_i = n_list.index(n_max)
            else:
                decided_i = random.choice([i for i, v in enumerate(v_list) if v == v_max])
        self.__state_now = self.__state_now.select_child_index(decided_i)
        self.__state_now.confirmed = True
        return decided_i
    
    def decide_manually(self, m:Move) -> None:
        """手動で手を決定し,木を更新する.
        相手の指し手を反映するときに使用する.

        Args:
            m (Move): 手
        """
        self.__state_now = self.__state_now.select_child_move(m)
        self.__state_now.confirmed = True

    def do_mcts(self) -> None:
        """MCTSを行い, 木を更新する.
        """
        self.__state_in_process: GameState = self.__state_now
        while True:
            self.__select()
            if not self.__expand():
                break
        result: tuple[int, int, int] = self.__evaluate()
        self.__backup(result)

    def __select(self) -> None:
        """処理するノードを選択し, __state_in_processに代入する."""
        while True:
            if self.__state_in_process.is_leaf():
                break
            # 子のucbリスト
            ucb_list = [c.calc_UCB1()
                        for c in self.__state_in_process.get_children()]
            ucb_max = max(ucb_list)
            # 未試行があればそれを選択
            if ucb_list.count(0) > 0:
                new_state_i = random.choice(
                    [i for i, ucb in enumerate(ucb_list) if ucb == 0])
                self.__state_in_process = self.__state_in_process.select_child_index(
                    new_state_i)
            # UCB最大から選択
            else:
                new_state_i = random.choice(
                    [i for i, ucb in enumerate(ucb_list) if ucb == ucb_max])
                self.__state_in_process = self.__state_in_process.select_child_index(
                    new_state_i)

    def __expand(self) -> bool:
        """条件を満たした場合, 子ノードを展開する.

        Returns:
            bool: 展開したか
        """
        if (self.__state_in_process.playout_result[1]+self.__state_in_process.playout_result[2] >= EXPAND_THRESHOLD
            or self.__state_in_process == self.__state_now):
            self.__state_in_process.gen_children(N_CHILD)    # 子の展開数
            return True
        return False

    def __evaluate(self, n: int = 1) -> tuple[int, int, int]:
        """プレイアウトをn回行い, 結果を返す.

        Args:
            n (int): evaluate実行回数. Defaults to 1.

        Returns:
            tuple[int,int,int]: プレイアウト結果
        """
        b: Board = self.__state_in_process.board
        results: list[int] = [self.__playout(b, PLAYOUT_STOP) for _ in range(n)]  # プレイアウト打ち切り回数
        return (len(results), results.count(0), results.count(1))

    def __backup(self, result: tuple[int, int, int]) -> None:
        """現在のノードの直前までプレイアウト結果を反映する.

        Args:
            result (tuple[int, int, int]): プレイアウト結果
        """
        while True:
            if self.__state_in_process == self.__state_now:
                break
            self.__state_in_process.apply_playout_result(result)
            self.__state_in_process = self.__state_in_process.select_parent()

    def __playout(self, b: Board, n_forward:int = -1) -> int:
        """プレイアウトを一回行い, 結果を返す.

        Args:
            b (Board): 開始盤面
            n_forward (int): 何手先までプレイアウトを行うか. -1の場合はゲーム終了まで.

        Returns:
            int: 勝者. -1:引き分け, 0:白, 1:黒
        """
        start = len(b.get_move_history())
        is_first = True    # 1手目のみスコアを計算し、リーチを取り逃がさないようにする
        while b.get_board_n() <= b.get_board_n_max() and (n_forward < 0 or len(b.get_move_history()) - start <= n_forward):
            legals: list[Move] = b.get_legal_move(calc_value=False, only_touch=True)
            is_first = False
            b.move(random.choice(legals))
            result: int = b.judge()
            if result is not None:
                break
        end = len(b.get_move_history())
        for _ in range(end - start):
            b.move_cancel()
        return result
