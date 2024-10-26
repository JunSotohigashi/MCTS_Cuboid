"""cuboid_gamestateモジュール
cuboidのゲーム木に関する機能を提供する.
"""

import math
import random
# import pydotplus  # 木画像保存時は有効化
from cuboid_manager import Board, Move


class GameState:
    """ゲーム木のノードとなるクラス
    各インスタンスは前の盤面からの指し手を保持する.
    """

    def __init__(self, move: Move = None, parent: 'GameState' = None) -> None:
        """ノードの初期化を行う.

        Args:
            move (Move): 親からの指し手
            parent (GameState|None, optional): 親ノードが存在する場合は指定する. Defaults to None.
        """
        self.__parent: 'GameState' = parent
        self.__children: list['GameState'] = []
        self.move_data: Move = move
        self.playout_result: tuple[int, int, int] = (0, 0, 0)
        self.board: Board = None
        self.confirmed: bool = False
        self.n_state: int = 0
        if self.__parent is None:
            self.board = Board()
            self.confirmed = True
        else:
            # 親の盤面からn_stateを1増やす
            self.n_state = self.__parent.n_state + 1

    def is_leaf(self) -> bool:
        """葉ノード(=子ノードなし)か判定する.

        Returns:
            bool: 葉ノードか?
        """
        return len(self.__children) == 0

    def get_parent(self) -> 'GameState':
        """親ノードを返す. 親がいない場合はNoneを返す.

        Returns:
            GameState: 親ノード
        """
        return self.__parent

    def get_children(self) -> list['GameState']:
        """子ノードのリストを返す. 子がいない場合は空リストを返す.

        Returns:
            list['GameState']: 子ノードのリスト
        """
        return self.__children

    def gen_children(self, k_children: int = -1) -> list['GameState']:
        """合法手を列挙し, 子ノードとして追加する.

        Returns:
            list['GameState']: 子ノードのリスト
        """
        assert self.board is not None
        if self.is_leaf():
            legals = self.board.get_legal_move(calc_value=True, only_touch=False)
            random.shuffle(legals)
            legals = sorted(legals, key=lambda m: m.value)
            self.__children = [GameState(m, self)
                               for m in legals[-k_children:]]
        return self.__children

    def select_parent(self) -> 'GameState':
        """親ノードを選択する.
        直前のmoveを取り消し, boardを譲渡する.

        Returns:
            GameState: 親ノード
        """
        assert self.board is not None
        self.board.move_cancel()
        self.__parent.board = self.board
        self.board = None
        return self.__parent

    def select_child_index(self, index: int) -> 'GameState':
        """子ノードを子のインデックスから選択する.
        選択されたノードに合わせてboardを更新し, boardを譲渡する.

        Args:
            index (int): 子ノードのインデックス

        Returns:
            GameState: 選択された子ノード
        """
        assert 0 <= index < len(self.__children)
        assert self.board is not None
        self.board.move(self.__children[index].move_data)
        self.__children[index].board = self.board
        self.board = None
        return self.__children[index]

    def select_child_move(self, m: Move) -> 'GameState':
        """子ノードを子のMoveから選択する.
        選択されたノードに合わせてboardを更新し, boardを譲渡する.

        Args:
            m (Move): 子ノードの指し手

        Returns:
            GameState: 選択された子ノード
        """
        assert self.board is not None
        for child in self.get_children():
            cm = child.move_data
            if ([m.x, m.y, m.dir] == [cm.x, cm.y, cm.dir]
                    and m.player == cm.player
                    and m.is_get == cm.is_get
                    and m.is_pass == cm.is_pass):
                self.board.move(cm)
                child.board = self.board
                self.board = None
                return child
        # 子が未展開
        legals:list[Move] = self.board.get_legal_move(calc_value=False, only_touch=False)
        for cm in legals:
            if ([m.x, m.y, m.dir] == [cm.x, cm.y, cm.dir]
                    and m.player == cm.player
                    and m.is_get == cm.is_get
                    and m.is_pass == cm.is_pass):
                child = GameState(cm, self)
                self.__children.append(child)
                self.board.move(cm)
                child.board = self.board
                self.board = None
                return child
        assert False, 'Illegal movement!'

    def apply_playout_result(self, result: tuple[int, int, int]) -> None:
        """プレイアウトの結果を反映する.

        Args:
            result (tuple[int,int,int]): プレイアウト結果
        """
        self.playout_result = (self.playout_result[0] + result[0],
                               self.playout_result[1] + result[1],
                               self.playout_result[2] + result[2])

    def calc_UCB1(self) -> float:
        """UCB1を算出する.

        Returns:
            float: UCB1
        """
        if self.playout_result[0] == 0:
            return 0
        else:
            n = self.playout_result[0]
            w = self.playout_result[self.move_data.player+1]
            t = sum([c.playout_result[0] for c in self.__parent.__children])
            return w / n + (2 * math.log(t) / n) ** 0.5

    def __str__(self) -> str:
        return f'GameState(n:{self.n_state} playout={self.playout_result} move:{self.move_data})'

    # 木画像保存時は以下を有効化
    # def __make_graph(self, graph: pydotplus.Dot):
    #     """子を再帰的に辿り, ノード・エッジ情報を列挙する.
    #     save_svg関数から使用する.

    #     Args:
    #         graph (pydotplus.Dot): 描画に使用するdotオブジェクト
    #     """   
    #     text = node_fcolor = node_tcolor = ''
    #     if self.get_parent() is not None:
    #         if self.move_data.player == 0:
    #             node_player = '#ffffff'
    #         else:
    #             node_player = '#000000'
    #         text = [f'<<table border="0" cellborder="1" cellspacing="0"><tr><td bgcolor="{node_player}"></td></tr>',
    #                 f'<tr><td><table border="0" cellborder="0" cellspacing="0">',
    #                 f'<tr><td>{self.move_data.x}, {self.move_data.y}, {self.move_data.dir}</td></tr>',
    #                 f'<tr><td>{self.move_data.value}</td></tr>',
    #                 f'<tr><td>{self.playout_result}</td></tr>',
    #                 f'<tr><td>{self.calc_UCB1():0.3f}</td></tr>',
    #                 f'</table></td></tr></table>>']
    #         text = ''.join(text)
    #     else:
    #         text = 'root'
    #         text = f'<<table border="0" cellborder="1" cellspacing="0"><tr><td bgcolor="#0000ff"><font color="#ffffff"><b>root</b></font></td></tr></table>>'
    #     graph.add_node(pydotplus.Node(id(self), label=text, shape='plain'))

    #     edge_color = ''
    #     edge_width = 0
    #     if self.confirmed:
    #         edge_color = '#ff0000'
    #         edge_width = 4
    #     else:
    #         edge_color = '#696969'
    #         edge_width = 1
    #     if self.get_parent() is not None:
    #         graph.add_edge(pydotplus.Edge(id(self.get_parent()), id(self),
    #                                       headport='n', tailport='s', color=edge_color, penwidth=edge_width))

    #     for c in self.get_children():
    #         c.__make_graph(graph)

    # def save_svg(self, path: str = 'gamestate.svg'):
    #     """現在のノードを根として, 木データのsvg画像を保存する.
    #     Args:
    #         path (str, optional): 保存先のパス. Defaults to 'gamestate.svg'.
    #     """
    #     graph = pydotplus.Dot('game_tree', graph_type='digraph', splines=False)
    #     self.__make_graph(graph)
    #     graph.write_svg(path)
