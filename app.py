import sys
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QTabWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import os
from datetime import datetime

from database import DatabaseManager
from payment_tab import PaymentTab
from expense_tab import ExpenseTab
from master_tab import MasterTab
from utils import get_latest_csv_file, log_message


class RadioBillingApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ラジオ局支払い・費用管理システム")
        # ウィンドウサイズを大きくする
        self.setGeometry(100, 100, 1400, 1600)  # x, y, width, height を調整

        # CSVデータフォルダを相対パスに変更
        self.csv_folder = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "data"
        )

        self.header_mapping = {
            "おもて情報.件名": "subject",
            "明細情報.明細項目": "project_name",
            "おもて情報.請求元": "payee",
            "おもて情報.支払先コード": "payee_code",
            "明細情報.金額": "amount",
            "おもて情報.自社支払期限": "payment_date",
            "状態": "status",
        }

        # メインウィジェットの作成
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        # メインレイアウト
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 上部フレーム - 説明ラベル
        label_frame = QFrame()
        label_layout = QVBoxLayout(label_frame)

        title_label = QLabel("支払い・費用データ管理システム")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("", 14, QFont.Bold))
        label_layout.addWidget(title_label)

        main_layout.addWidget(label_frame)

        # タブコントロールの作成
        self.tab_control = QTabWidget()
        self.tab_control.setDocumentMode(True)  # よりモダンな外観にする
        self.tab_control.setTabPosition(QTabWidget.North)  # タブの位置を上部に
        self.tab_control.setMovable(False)  # タブの移動を禁止
        self.tab_control.setTabsClosable(False)  # 閉じるボタンなし

        # タブバーに余分なスペースを確保
        self.tab_control.tabBar().setExpanding(False)  # タブが等幅にならないようにする
        self.tab_control.tabBar().setElideMode(Qt.ElideNone)  # テキストの省略を無効化

        main_layout.addWidget(self.tab_control)

        # ステータスフレーム
        status_frame = QFrame()
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(0, 5, 0, 0)

        self.status_label = QLabel("読み込み中...")
        self.status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.status_label.setFont(QFont("", 10))
        status_layout.addWidget(self.status_label)

        # 余白を追加
        status_layout.addStretch()

        # 最後に更新表示用
        self.last_update_label = QLabel("")
        self.last_update_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.last_update_label.setFont(QFont("", 10))
        status_layout.addWidget(self.last_update_label)

        main_layout.addWidget(status_frame)

        # データベースマネージャーの初期化
        self.db_manager = DatabaseManager()
        self.db_manager.init_db()

        # タブの作成
        self.payment_tab = PaymentTab(self.tab_control, self)
        self.tab_control.addTab(self.payment_tab, "支払い情報 (閲覧専用)")

        self.expense_tab = ExpenseTab(self.tab_control, self)
        self.tab_control.addTab(self.expense_tab, "費用管理")

        self.master_tab = MasterTab(self.tab_control, self)
        self.tab_control.addTab(self.master_tab, "費用マスター")

        # データを読み込み
        self.import_latest_csv()
        self.expense_tab.refresh_data()
        self.master_tab.refresh_data()

        self.apply_stylesheet()  # 基本的な視認性を確保

    def apply_stylesheet(self):
        # PC標準の配色でシンプルに
        style = """
            QTreeWidget {
                font-size: 13px;
                gridline-color: #d0d0d0;
                alternate-background-color: #f5f5f5;
            }
            QTreeWidget::item:selected {
                background-color: #3399ff;
                color: white;
            }
            QLabel {
                font-size: 13px;
            }
            QPushButton {
                font-size: 13px;
                padding: 6px 12px;
                min-height: 20px;
            }
            QLineEdit {
                font-size: 13px;
                padding: 4px;
            }
            QComboBox {
                font-size: 13px;
                padding: 4px;
            }
            QDateEdit {
                font-size: 13px;
                padding: 4px;
            }
        """
        self.setStyleSheet(style)

    def import_latest_csv(self):
        """最新のCSVファイルからデータをインポート"""
        csv_file = get_latest_csv_file(self.csv_folder)

        if not csv_file:
            self.status_label.setText("CSVファイルが見つかりません")
            return False

        try:
            # CSVファイルの情報を更新
            file_size = os.path.getsize(csv_file) // 1024  # KBに変換
            file_time = datetime.fromtimestamp(os.path.getmtime(csv_file)).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            file_name = os.path.basename(csv_file)

            self.payment_tab.csv_info_label.setText(f"CSV: {file_name} ({file_size}KB)")

            # データをインポート
            row_count = self.db_manager.import_csv_data(csv_file, self.header_mapping)

            log_message(
                f"{row_count}件のデータをCSVからインポートしました: {file_name}"
            )

            # データを表示
            self.payment_tab.refresh_data()
            self.status_label.setText(
                f"{row_count}件のデータをCSVからインポートしました"
            )

            return True

        except Exception as e:
            log_message(f"CSVファイルのインポート中にエラー: {e}")
            import traceback

            log_message(traceback.format_exc())
            self.status_label.setText(f"CSVファイルの読み込みに失敗しました: {str(e)}")
            return False

    def reload_data(self):
        """データの再読み込み"""
        success = self.import_latest_csv()
        if success:
            self.status_label.setText("データを再読み込みしました")
        else:
            self.status_label.setText("データの再読み込みに失敗しました")


def main():
    app = QApplication(sys.argv)
    
    # Windows高DPI対応
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    window = RadioBillingApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

# ファイル終了確認用のコメント - app.py完了
