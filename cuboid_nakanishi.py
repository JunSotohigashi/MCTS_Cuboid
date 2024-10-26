"""server.pyを介してCuboid対戦を行うプレイヤー"""
import time
import threading
from cuboid_mcts import UCT_MCTS
from cuboid_manager import Move

TIME_THINK = 4.0
TIME_THINK_2 = 2.0


class MCTSPlayer:
    """プレイヤーとして手を受け取り、次の手を決定する
    """
    def __init__(self, player: int, time_limit = 1.0, time_limit_get = 0.5) -> None:
        """コンストラクタ

        Args:
            player (int): プレイヤー番号 白:1 黒:2
            time_limit (float, optional): getある場合、get思考時間. Defaults to 1.0.
            time_limit_get (float, optional): 最大思考時間. Defaults to 0.5.
        """
        self.__TIME_LIMIT_GET = time_limit_get
        self.__TIME_LIMIT = time_limit
        self.__player = player-1    # 自分のプレイヤー番号 白:0 黒:1
        self.__mcts = UCT_MCTS()
        self.__last_state_enemy: list[int] = []
        self.__need_to_get: bool = False

    def __resolve_last_move(self, state: str):
        """server.pyから送られた文字列から、直前の相手のMoveを逆算し、木データを更新する.

        Args:
            state (str): server.pyからの生文字列
        """
        state_enemy: list[tuple[int, int, int, int]] = []
        # 相手の駒情報を抽出する
        state_split = list(map(int, state.split()))
        for i in range(2, len(state_split), 5):
            if state_split[i] != self.__player+1:
                state_enemy.append(
                    (state_split[i+1], state_split[i+2], state_split[i+3], state_split[i+4]))
        moves: list[Move] = []
        if len(state_enemy) == 0:
            return
        elif len(state_enemy) != len(self.__last_state_enemy):
            # 新しく駒putした
            x = min(state_enemy[-1][0], state_enemy[-1][2]) - 1
            y = min(state_enemy[-1][1], state_enemy[-1][3]) - 1
            dir = None
            if state_enemy[-1][0] != state_enemy[-1][2] and state_enemy[-1][1] == state_enemy[-1][3]:
                dir = 0
            elif state_enemy[-1][0] == state_enemy[-1][2] and state_enemy[-1][1] != state_enemy[-1][3]:
                dir = 1
            else:
                dir = 2
            moves.append(Move((self.__player+1) % 2, x, y, dir, is_get=False))
        else:
            # get元を探す
            for crd_old, crd_new in zip(self.__last_state_enemy, state_enemy):
                if crd_old != crd_new:
                    x = min(crd_old[0], crd_old[2]) - 1
                    y = min(crd_old[1], crd_old[3]) - 1
                    dir = None
                    if crd_old[0] != crd_old[2] and crd_old[1] == crd_old[3]:
                        dir = 0
                    elif crd_old[0] == crd_old[2] and crd_old[1] != crd_old[3]:
                        dir = 1
                    else:
                        dir = 2
                    moves.append(Move((self.__player+1) %
                                 2, x, y, dir, is_get=True))
                    break
            # put
            x = min(state_enemy[-1][0], state_enemy[-1][2]) - 1
            y = min(state_enemy[-1][1], state_enemy[-1][3]) - 1
            dir = None
            if state_enemy[-1][0] != state_enemy[-1][2] and state_enemy[-1][1] == state_enemy[-1][3]:
                dir = 0
            elif state_enemy[-1][0] == state_enemy[-1][2] and state_enemy[-1][1] != state_enemy[-1][3]:
                dir = 1
            else:
                dir = 2
            moves.append(Move((self.__player+1) % 2, x, y, dir, is_get=False))

        self.__last_state_enemy = state_enemy
        # 推定したmoveを木に反映
        for m in moves:
            with open('moniter.txt', mode='a') as f:
                print(m, file=f)
            self.__mcts.decide_manually(m)
            with open('moniter.txt', mode='a') as f:
                print(self.__mcts.get_board(), file=f)

    def read_state(self, state:str) -> bool:
        """server.pyから盤面情報を受け取る.

        Returns:
            bool: ゲームセット?
        """
        if state == '-1':
            # ゲームセットでプログラムを終了する
            return True
        self.__resolve_last_move(state)
        self.__need_to_get = (int(state.split()[self.__player]) == 0)

    def decide_move(self) -> tuple[Move, Move]:
        """MCTSを利用して次の手を決定する.

        Returns:
            tuple[Move, Move]: put,get. getない場合はNone.
        """
        time_start = time.time()
        move_get: Move = None
        move_put: Move = None
        if self.__need_to_get:
            # 取得ありの場合は時間配分しmoveデータを2つ生成
            while time.time() - time_start < self.__TIME_LIMIT_GET:
                self.__mcts.do_mcts()
            self.__mcts.decide()
            move_get = self.__mcts.get_board().get_move_history()[-1]
            while time.time() - time_start < self.__TIME_LIMIT:
                self.__mcts.do_mcts()
            self.__mcts.decide()
            move_put = self.__mcts.get_board().get_move_history()[-1]
        else:
            # 取得なしの場合は時間いっぱい
            while time.time() - time_start < self.__TIME_LIMIT:
                self.__mcts.do_mcts()
            self.__mcts.decide()
            move_put = self.__mcts.get_board().get_move_history()[-1]
        return move_put, move_get

    def update_tree(self):
        self.__mcts.do_mcts()

    def save_tree_svg(self):
        """木データを画像として保存する.
        """
        # self.__mcts.state_root.save_svg(f"gamestate_{id(self)}.svg")
        self.__mcts.state_root.save_svg(f"gamestate.svg")

    @staticmethod
    def gen_move_msg(move_put: Move, move_get: Move = None) -> str:
        """Moveデータを、server.pyが解釈できる文字列に変換する.

        Args:
            move_put (Move): putのMoveデータ
            move_get (Move, optional): getのMoveデータ. Defaults to None.

        Returns:
            str: 変換された文字列
        """
        put_x1 = move_put.x
        put_y1 = move_put.y
        put_x2 = move_put.x+1 if move_put.dir == 0 else put_x1
        put_y2 = move_put.y+1 if move_put.dir == 1 else put_y1
        if move_get is None:
            return f'{put_x1+1} {put_y1+1} {put_x2+1} {put_y2+1}'
        get_x1 = move_get.x
        get_y1 = move_get.y
        get_x2 = move_get.x+1 if move_get.dir == 0 else get_x1
        get_y2 = move_get.y+1 if move_get.dir == 1 else get_y1
        return f'{put_x1+1} {put_y1+1} {put_x2+1} {put_y2+1} {get_x1+1} {get_y1+1} {get_x2+1} {get_y2+1}'

def input_thread(result:list):
    """別スレッドでinputを行い入力された文字列を返す.
    結果を元スレッドに返すため, ミュータブルなオブジェクトを利用する.
    リストの0要素目に結果を格納する.

    Args:
        result (list): 入力された文字列を格納するリスト
    """
    result[0] = input()

def main():
    # プレイヤー番号の受け取り
    player_id = int(input())
    # 処理猶予時間の設定はココ
    mcts_player = MCTSPlayer(player_id, TIME_THINK, TIME_THINK_2)
    print(player_id)
    # 対戦の開始
    while True:
        # 別スレッドでinput待機し, 待ち時間にMCTSを更新し続ける
        input_result = [None]
        input_hundle = threading.Thread(target=input_thread, args=(input_result,), daemon=True)
        input_hundle.start()
        # mcts_player.save_tree_svg()   # 木画像保存
        while True:
            mcts_player.update_tree()   # MCTS木更新
            if not input_hundle.is_alive():  # inputされるまで繰り返す
                break
        state = input_result[0] # 結果の受け取り
        
        # state = input()   # バックグラウンド動作なし

        game_over = mcts_player.read_state(state)
        if game_over:
            # ゲームセットでプログラムを終了する
            break
        move_put, move_get = mcts_player.decide_move()
        msg = MCTSPlayer.gen_move_msg(move_put, move_get)
        print(msg)


if __name__ == '__main__':
    main()
