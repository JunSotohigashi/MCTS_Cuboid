"""cuboid_managerモジュール
cuboidのゲーム進行に関する基本的な機能を提供する.
"""

###### Constants ######
# 駒の向きによる2つめのブロックの相対座標 x方向,y方向,z方向
DIRECTION: list[list[int]] = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
# 接触判定用の座標オフセット
TOUCH: list[list[int]] = [[0, -1, 0], [1, 0, 0], [0, 1, 0],
                          [-1, 0, 0], [0, 0, 1], [0, 0, -1]]
# TOUCHの反転用辞書 TOUCHのインデックスを反転する
TOUCH_INV: dict[int:int] = {0: 2, 1: 3, 2: 0, 3: 1, 4: 5, 5: 4}


class Move:
    """駒の移動を表すデータクラス"""

    def __init__(self, player: int, x: int = -1, y: int = -1, dir: int = -1, is_get: bool = False, is_pass: bool = False, value: int = 0) -> None:
        """
        Args:
            player (int): プレイヤー番号 0:白, 1:黒
            x (int, optional): 駒1つ目x座標. Defaults to -1.
            y (int, optional): 駒1つ目y座標. Defaults to -1.
            dir (int, optional): 駒の向き. 0:x, 1:y, 2:z方向. Defaults to -1.
            is_get (bool, optional): get動作ならTrue. Defaults to False.
            is_pass (bool, optional): パスならTrue. Defaults to False.
            value (floar, optional): プレイアウトでの選択確率. Defaults to 0.
        """
        self.player: int = player
        self.x: int = x
        self.y: int = y
        self.dir: int = dir
        self.is_get: bool = is_get
        self.is_pass: bool = is_pass
        self.value: float = value

    def __str__(self) -> str:
        return f'Move(player={self.player}, x,y,dir={self.x,self.y,self.dir}, is_get={self.is_get}, is_pass={self.is_pass}, value={self.value}, id={id(self)})'


class Board:
    """Cuboidの盤面を保持・操作するクラス"""

    def __init__(self, max_x: int = 10, max_y: int = 10, max_piece: int = 16, max_n: int = 300) -> None:
        """空盤面でインスタンスを初期化する."""
        # ゲームの基本設定を行う
        self.__MAX_X = max_x              # x方向盤面サイズ
        self.__MAX_Y = max_y              # y方向盤面サイズ
        self.__MAX_PIECE = max_piece      # 1人当たりの所持駒数
        self.__MAX_N = max_n              # ゲームセットとなる手数
        # 各コマを構成するブロックの座標リスト
        # 最大駒数*2(駒に含まれるブロック)*2(プレイヤー数)個用意する.
        # 駒を構成するブロックはx,y,zの順で昇順にして代入する.
        self.__block_xyz: list[list[int]] = [
            [-1] * 3 for _ in range(self.__MAX_PIECE*4)]
        # 各マスの現在の最大高さ
        self.__max_z: list[list[int]] = [
            [0] * self.__MAX_X for _ in range(self.__MAX_Y)]
        # 各ブロックに接触しているブロックの指標を, 北,東,南,西,上,下の順で格納する.
        self.__touch: list[list[int]] = [
            [-1] * 6 for _ in range(self.__MAX_PIECE*4)]
        # moveの履歴
        self.__move_history: list[Move] = []
        self.__board_n = 0

    def get_move_history(self) -> list[Move]:
        """Moveの履歴を返す.

        Returns:
            list[Move]: Move履歴
        """
        return self.__move_history

    def get_board_n(self) -> int:
        """現在の手数を返す.

        Returns:
            int: 手数
        """
        return self.__board_n

    def get_board_n_max(self) -> int:
        """盤面最大手数を返す.

        Returns:
            int: 最大手数
        """
        return self.__MAX_N

    def __put(self, m: Move) -> int:
        """駒を置く.

        Args:
            m (Move): 置くMoveデータ

        Returns:
            int: 置いた駒の番号
        """
        assert m.player in [0, 1], 'Unknown player'
        assert not m.is_pass
        assert not m.is_get
        assert 0 <= m.x < (self.__MAX_X-1 if m.dir == 0
                           else self.__MAX_X), 'x is out of board'
        assert 0 <= m.y < (self.__MAX_Y-1 if m.dir == 1
                           else self.__MAX_Y), 'y is out of board'
        assert m.dir in [0, 1, 2], 'Unknown direction'
        # getと違う場所か?
        assert (len(self.__move_history) == 0
                or not self.__move_history[-1].is_get
                or (self.__move_history[-1].player == m.player
                    and self.__move_history[-1].x != m.x
                    or self.__move_history[-1].y != m.y
                    or self.__move_history[-1].dir != m.dir)), 'Same position'
        assert self.__max_z[m.y][m.x] == (self.__max_z[m.y+DIRECTION[m.dir][1]]
                                                      [m.x+DIRECTION[m.dir][0]]), 'Block cannot float in air'
        # ブロックのインデックスを取得する.
        target: int = self.__block_xyz[::2].index([-1, -1, -1], m.player*self.__MAX_PIECE,
                                                  (m.player+1)*self.__MAX_PIECE) * 2
        # ブロック1つめを置く.
        xyz1 = [m.x, m.y, self.__max_z[m.y][m.x]]
        self.__block_xyz[target] = xyz1
        self.__max_z[xyz1[1]][xyz1[0]] += 1
        # ブロック2つめを置く.
        xyz2 = [i+j for i, j in zip(xyz1, DIRECTION[m.dir])]
        self.__block_xyz[target+1] = xyz2
        assert self.__max_z[xyz2[1]][xyz2[0]] == xyz2[2]
        self.__max_z[xyz2[1]][xyz2[0]] += 1
        # ブロックの隣接情報に当該ブロックを追加する.
        target1_touch = [
            [c+o for c, o in zip(self.__block_xyz[target], offset)] for offset in TOUCH]
        target2_touch = [
            [c+o for c, o in zip(self.__block_xyz[target+1], offset)] for offset in TOUCH]
        for i in range(self.__MAX_PIECE*4):
            if self.__block_xyz[i] == [-1, -1, -1]:
                continue
            for j, (t1, t2) in enumerate(zip(target1_touch, target2_touch)):
                if t1 == self.__block_xyz[i]:
                    self.__touch[target][j] = i
                    self.__touch[i][TOUCH_INV[j]] = target
                if t2 == self.__block_xyz[i]:
                    self.__touch[target+1][j] = i
                    self.__touch[i][TOUCH_INV[j]] = target+1
        return target//2

    def __get(self, m: Move) -> int:
        """駒を取る.

        Args:
            m (Move): 取るMove

        Returns:
            int: 取った駒の番号
        """
        assert m.player in [0, 1], 'Unknown player'
        assert not m.is_pass
        assert m.is_get
        assert 0 <= m.x < (self.__MAX_X-1 if m.dir == 0
                           else self.__MAX_X), 'x is out of board'
        assert 0 <= m.y < (self.__MAX_Y-1 if m.dir == 1
                           else self.__MAX_Y), 'y is out of board'
        assert m.dir in [0, 1, 2], 'Unknown direction'
        # ブロックのインデックスを取得する.
        xy = [m.x, m.y]
        target = None
        for i in range(m.player*self.__MAX_PIECE, (m.player+1)*self.__MAX_PIECE):
            if self.__block_xyz[i*2][:2] == xy:
                # 対象の駒か?
                if ((m.dir == 2 and self.__block_xyz[i*2+1][2] == self.__max_z[xy[1]][xy[0]]-1)
                        or (m.dir != 2 and self.__block_xyz[i*2][2] == self.__max_z[xy[1]][xy[0]]-1)):
                    target = i*2
                    break
        assert self.__block_xyz[target][:2] == xy
        assert self.__block_xyz[target+1][:2] == [i + j for i, j
                                                  in zip(xy, DIRECTION[m.dir][:2])]
        # ブロック1つめを取る.
        self.__block_xyz[target] = [-1, -1, -1]
        self.__max_z[xy[1]][xy[0]] -= 1
        # ブロック2つめを取る.
        xy = [i+j for i, j in zip(xy, DIRECTION[m.dir][:2])]
        self.__block_xyz[target+1] = [-1, -1, -1]
        self.__max_z[xy[1]][xy[0]] -= 1
        # ブロックの隣接情報から当該ブロックを削除する.
        for i in range(self.__MAX_PIECE*4):
            if self.__block_xyz[i] == [-1, -1, -1]:
                continue
            for t in range(6):
                if self.__touch[i][t] == target:
                    self.__touch[i][t] = -1
                if self.__touch[i][t] == target+1:
                    self.__touch[i][t] = -1
        self.__touch[target] = [-1] * 6
        self.__touch[target+1] = [-1] * 6
        return target//2

    def move(self, m: Move) -> int:
        """盤面にMoveを適用する.

        Args:
            m (Move): 指し手

        Returns:
            int: 操作した駒の番号
        """
        piece = None
        if m.is_pass:
            self.__board_n += 1
        elif m.is_get:
            piece = self.__get(m)
        else:
            piece = self.__put(m)
            self.__board_n += 1
        # historyに追加
        self.__move_history.append(m)
        return piece

    def move_cancel(self) -> None:
        """直前のMoveを取り消す."""
        if len(self.__move_history) == 0:
            return
        m = self.__move_history.pop()
        m = Move(m.player, m.x, m.y, m.dir, not m.is_get, m.is_pass, m.value)
        if m.is_pass:
            self.__board_n -= 1
        elif m.is_get:
            self.__get(m)
            self.__board_n -= 1
        else:
            self.__put(m)

    def __north_recursive(self, target: int, touch_north: list[bool]) -> None:
        """北側のエッジにあるブロックから, 連続するブロックを再帰的に判定する.
        judge関数から使用する.

        Args:
            target (int): 注目するブロックのインデックス
            touch_north (list[bool]): 各ブロックが北側エッジから連続しているかのフラグリスト
        """
        touch_north[target] = True
        for i in self.__touch[target]:
            if (i < 0 or i == target
                    or (target // (self.__MAX_PIECE*2) != i // (self.__MAX_PIECE*2))):
                continue
            elif not touch_north[i]:
                self.__north_recursive(i, touch_north)

    def judge(self) -> int:
        """現在の盤面に対して, 勝者の判定を行う.

        Returns:
            int: 勝者の番号.(None:未確定, -1:引き分け, 0:白, 1:黒)
        """
        # 北側・南側のエッジにあるブロックをそれぞれ列挙する.
        touch_north = [b[1] == 0 and b[2] == 0 for b in self.__block_xyz]
        touch_south = [b[1] == self.__MAX_Y -
                       1 and b[2] == 0 for b in self.__block_xyz]
        # 北側のエッジにあるブロックから連続するブロックを探索し, touch_northを更新する.
        for target, north in enumerate(touch_north):
            if north:
                self.__north_recursive(target, touch_north)
        # touch_northかつtouch_southのブロックがあれば, 両端がつながっているので勝利.
        for i, (n, s) in enumerate(zip(touch_north, touch_south)):
            if n and s:
                return i // (self.__MAX_PIECE*2)
        # ゲーム終了か引き分けか判定する.
        if self.__board_n >= self.__MAX_N:
            return -1
        return None

    def __calc_value(self, m: Move) -> Move:
        """Moveの価値を計算し, valueを更新する.

        Args:
            m (Move): valueを計算したいMove

        Returns:
            Move: valueが計算されたMove
        """
        if m.is_pass:
            return m
        val = 0
        if m.is_get:
            val_dir = val_touch = 0
            # 方向ボーナス
            val_dir += [5,1,10][m.dir]
            # 隣接ブロック数少ないほどいい
            piece = self.move(m)*2
            self.move_cancel()
            val_touch += (self.__touch[piece][:4].count(-1)
                          + self.__touch[piece+1][:4].count(-1))
            val = val_dir*1.0 + val_touch*2.0
        else:
            val_dir = val_even = val_edge = val_manhattan = val_touch = val_reach= 0
            # 方向ボーナス
            val_dir += [3,5,1][m.dir]
            val_even = 1 if m.x+m.y % 2 == 0 else 0
            piece = self.move(m)*2
            # 最初はエッジを取りたい
            val_edge += 1 if (self.__block_xyz[piece][1] == 0 and self.__block_xyz[piece][2] == 0) else 0
            val_edge += 1 if (self.__block_xyz[piece+1][1] == self.__MAX_Y-1 and self.__block_xyz[piece+1][2] == 0) else 0

            manhattan0 = manhattan1 = 1000
            for i,p in enumerate(self.__block_xyz):
                # 未設置のブロックはスキップ
                if p == [-1,-1,-1]:
                    continue
                # 自ブロックはスキップ
                if i == piece or i == piece+1:
                    continue
                if i%self.__MAX_PIECE != m.player:
                    continue
                manhattan = (abs(self.__block_xyz[piece][0] - p[0])
                             +abs(self.__block_xyz[piece][1] - p[1])
                             +abs(self.__block_xyz[piece][2] - p[2]))
                if manhattan < manhattan0:
                    manhattan0 = manhattan
                manhattan = (abs(self.__block_xyz[piece+1][0] - p[0])
                             +abs(self.__block_xyz[piece+1][1] - p[1])
                             +abs(self.__block_xyz[piece+1][2] - p[2]))
                if manhattan < manhattan1:
                    manhattan1 = manhattan
            if manhattan0 == 3:
                val_manhattan += 2
            if manhattan1 == 3:
                val_manhattan += 2

            # touch_score_my = [5,2,4,2,0,1]
            # touch_score = [2,2,2,2,0,1]
            # for i,(piece_touch0,piece_touch1) in enumerate(zip(self.__touch[piece],self.__touch[piece+1])):
            #     # val_touch += 0 if piece_touch0 == -1 else (touch_score_my[i] if piece_touch0%self.__MAX_PIECE == m.player else touch_score[i])
            #     val_touch += 0 if piece_touch1 == -1 else (touch_score_my[i] if piece_touch1%self.__MAX_PIECE == m.player else touch_score[i])
            # 隣接ブロック
            touch_score = [[4,0,1,2,0,0,4,2,1,0,0,0],
                           [10,2,0,2,0,0,0,1,3,1,0,0],
                           [3,1,1,1,0,0,1,1,1,1,0,0]]
            for i,p in enumerate(self.__touch[piece]+self.__touch[piece+1]):
                if p != -1:
                    val_touch += touch_score[m.dir][i]
            if m.dir == 0 and self.__touch[piece][0]//2 == self.__touch[piece+1][0]//2 == m.player:
                val_touch -= 4
            elif m.dir == 0 and self.__touch[piece][2]//2 == self.__touch[piece+1][2]//2 == m.player:
                val_touch -= 4
            elif m.dir == 1 and self.__touch[piece][1]//2 == self.__touch[piece+1][1]//2 == m.player:
                val_touch -= 2
            elif m.dir == 1 and self.__touch[piece][3]//2 == self.__touch[piece+1][3]//2 == m.player:
                val_touch -= 2


            # 自分のあがり手
            val_reach += 1 if self.judge() is not None else 0
            self.move_cancel()
            # 相手のリーチを潰す
            # TODO 駒の数16使用済みの場合の処理
            try:
                self.move(Move((m.player+1) % 2, m.x, m.y, m.dir))
                val_reach += 1 if self.judge() is not None else 0
                self.move_cancel()
            except:
                pass
            val = (val_dir*2.0
                   + val_edge * 1.0
                   + val_touch * 4.0
                   + val_even * 1.0
                   + val_manhattan * 1.0
                   + val_reach * 10000.0)

        # 計算結果を反映
        m.value = val
        return m


    def get_legal_move(self, calc_value:bool = False, only_touch: bool = False) -> list[Move]:
        """現在の盤面からの合法手を列挙する.

        Returns:
            list[Move]: 合法手のリスト. 各手のvalueは__calc_value関数で計算される.
        """
        player = is_get = None
        if len(self.__move_history) == 0:
            player = 0
            is_get = False
        elif self.__move_history[-1].is_get:
            player = self.__move_history[-1].player
            is_get = False
        else:
            player = (self.__move_history[-1].player + 1) % 2
            for i in range(player*self.__MAX_PIECE*2, (player+1)*self.__MAX_PIECE*2, 2):
                if self.__block_xyz[i] == [-1, -1, -1]:
                    is_get = False
                    break
            else:
                is_get = True
        legal_moves = []
        if is_get:
            # getの場合
            for i in range(player*self.__MAX_PIECE*2, (player+1)*self.__MAX_PIECE*2, 2):
                # z方向の駒 上に別のブロックなし
                if (self.__block_xyz[i][:2] == self.__block_xyz[i+1][:2]
                    and self.__block_xyz[i+1][2] == self.__max_z[self.__block_xyz[i+1][1]][self.__block_xyz[i+1][0]]-1):
                    legal_moves.append(Move(player, self.__block_xyz[i][0], self.__block_xyz[i][1], 2, is_get=True))
                    continue
                # xy方向 それぞれ上に別のブロックなし
                if (self.__block_xyz[i][2]
                    == self.__max_z[self.__block_xyz[i][1]][self.__block_xyz[i][0]]-1
                    == self.__max_z[self.__block_xyz[i+1][1]][self.__block_xyz[i+1][0]]-1):
                    if self.__block_xyz[i][1] == self.__block_xyz[i+1][1]:
                        # x方向
                        legal_moves.append(Move(player, self.__block_xyz[i][0], self.__block_xyz[i][1], 0, is_get=True))
                    else:
                        # y方向
                        legal_moves.append(Move(player, self.__block_xyz[i][0], self.__block_xyz[i][1], 1, is_get=True))
        else:
            # putの場合
            legal_xydir = set()
            if only_touch:
                z0_xy = set()   # コマ周囲かつz=0のxy座標
                for x in range(self.__MAX_X):
                    for y in range(self.__MAX_Y):
                        if self.__max_z[y][x] > 0:
                            if x > 0 and self.__max_z[y][x-1] == 0:
                                z0_xy.add((x-1,y))
                            if x < self.__MAX_X-1 and self.__max_z[y][x+1] == 0:
                                z0_xy.add((x+1,y))
                            if y > 0 and self.__max_z[y-1][x] == 0:
                                z0_xy.add((x,y-1))
                            if y < self.__MAX_Y-1 and self.__max_z[y+1][x] == 0:
                                z0_xy.add((x,y+1))
                for xy in z0_xy:
                    if xy[0] > 0 and self.__max_z[xy[1]][xy[0]-1] == 0:
                        legal_xydir.add((xy[0]-1, xy[1], 0))
                    if xy[0] < self.__MAX_X-1 and self.__max_z[xy[1]][xy[0]+1] == 0:
                        legal_xydir.add((xy[0], xy[1], 0))
                    if xy[1] > 0 and self.__max_z[xy[1]-1][xy[0]] == 0:
                        legal_xydir.add((xy[0], xy[1]-1, 1))
                    if xy[1] < self.__MAX_Y-1 and self.__max_z[xy[1]+1][xy[0]] == 0:
                        legal_xydir.add((xy[0], xy[1], 1))
                    legal_xydir.add((xy[0], xy[1], 2))
            else:
                for x in range(self.__MAX_X):
                    for y in range(self.__MAX_Y):
                        # x方向
                        if x < self.__MAX_X-1 and self.__max_z[y][x] == self.__max_z[y][x+1]:
                            legal_xydir.add((x, y, 0))
                        # y方向
                        if y < self.__MAX_Y-1 and self.__max_z[y][x] == self.__max_z[y+1][x]:
                            legal_xydir.add((x, y, 1))
                        # z方向
                        legal_xydir.add((x, y, 2))
            # 直前がgetなら同じ座標を除去
            if len(self.__move_history) > 0 and self.__move_history[-1].is_get:
                if (self.__move_history[-1].x, self.__move_history[-1].y, self.__move_history[-1].dir) in legal_xydir:
                    legal_xydir.remove((self.__move_history[-1].x, self.__move_history[-1].y, self.__move_history[-1].dir))
            legal_moves = [Move(player,x,y,d,is_get) for x,y,d in legal_xydir]
        if calc_value:
            return list(map(self.__calc_value, legal_moves))
        else:
            return legal_moves

    def __str__(self) -> str:
        """Boardを文字列にフォーマットする.

        Returns:
            str: 文字列に変換されたBoardデータ
        """
        # 駒の番号を文字列に変換し, 3D整数から2D文字列にする.
        z_max = max([max(row) for row in self.__max_z])
        board_matrix = [
            [[None] * z_max for _ in range(self.__MAX_X)] for _ in range(self.__MAX_Y)]
        for i, block in enumerate(self.__block_xyz):
            if block == [-1, -1, -1]:
                continue
            board_matrix[block[1]][block[0]][block[2]] = i
        # 各座標の駒を2D文字列リストで格納する.
        str_board = []
        for y in range(self.__MAX_Y):
            y_text = []
            for x in range(self.__MAX_X):
                x_text_list = []
                for z in range(z_max):
                    if board_matrix[y][x][z] is None:
                        break
                    elif board_matrix[y][x][z] < self.__MAX_PIECE*2:
                        x_text_list.append('W')
                    else:
                        x_text_list.append('B')
                x_text = ''.join(x_text_list)
                y_text.append(x_text)
            str_board.append(y_text)
        # 表での列の幅を決定するため, ラベルと駒の文字数の最大値を調べる.
        str_max_z = [max([len(str_board[y][x]) for y in range(self.__MAX_Y)])
                     for x in range(self.__MAX_X)]
        str_max_x = len(str(self.__MAX_X - 1))
        str_max_y = len(str(self.__MAX_Y - 1))
        # 表の文字列を生成する.
        # タイトル行
        text_list = [f'Board(n={self.__board_n}, id={id(self)})\n']
        text_list.append(
            '┌'+'─'*str_max_y+'┬'+''.join(['──'+'─'*max(str_max_x, z) for z in str_max_z])+'┐\n')
        text_list.append(
            '│'+' '*str_max_y+'│'+''.join(['  '+str(x).ljust(max(str_max_x, z)) for x, z in enumerate(str_max_z)])+'│\n')
        text_list.append(
            '├'+'─'*str_max_y+'┼'+''.join(['──'+'─'*max(str_max_x, z) for z in str_max_z])+'┤\n')
        # 駒データ
        for y, line in enumerate(str_board):
            text_list.append(
                '│'+str(y).center(str_max_y)+'│'+''.join(['  '+data.ljust(max(str_max_x, z)) for data, z in zip(line, str_max_z)])+'│\n')
        text_list.append(
            '└'+'─'*str_max_y+'┴'+''.join(['──'+'─'*max(str_max_x, z) for z in str_max_z])+'┘')
        # 生成したすべての文字列を結合して返す.
        return ''.join(text_list)
