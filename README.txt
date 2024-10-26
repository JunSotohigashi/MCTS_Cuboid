2023年度ソフトウェア実験 "Cuboid"
21062 中西 純


ファイル構成
    README.txt             このファイル
    cuboid_nakanishi.py    server.pyから呼び出すメインプログラム
    cuboid_mcts.py         モンテカルロ木探索を行うサブモジュール
    cuboid_gamestate.py    ゲーム木のサブモジュール
    cuboid_manager.py      盤面の保持と操作を行うサブモジュール


必要環境
    Python 3.10.6
    wrapt_timeout_decorator
    インストールコマンド例
        $ pip install wrapt_timeout_decorator


使用方法
    cuboid_nakanishi.pyをserver.pyのプレイヤーとして指定する。
    $ python ./server.py -1 ./cuboid_nakanishi.py -2 ./random_player.py


木データの保存方法
    ゲーム木を画像として保存する場合は以下のライブラリ・ソフトが追加で必要です。
        pydotplus
        graphviz
        インストールコマンド例
            $ pip install pydotplus
            $ sudo apt update
            $ sudo apt install graphviz
    プログラムの以下の箇所をアンコメントしてください。
        cuboid_nakanishi.py 187行目
            mcts_player.save_tree_svg()
        cuboid_gamestate.py 7行目
            import pydotplus
        cuboid_gamestate.py 末尾
            __make_graph関数とsave_svg関数
    実行すると、1手ごとに'gamestate.svg'に保存されます。

