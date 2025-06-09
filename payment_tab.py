from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QHeaderView,
    QScrollArea,
    QFrame,
    QGridLayout,
    QGroupBox,
    QLineEdit,
    QComboBox,
    QDateEdit,
    QFileDialog,
    QMessageBox,
    QCheckBox,
)
from PyQt5.QtCore import Qt, QDate, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QColor, QFont, QBrush
from utils import format_amount, log_message


class PaymentTab(QWidget):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.db_manager = app.db_manager
        self.status_label = app.status_label

        # ソート情報
        self.sort_info = {"column": None, "reverse": False}

        # 色分け設定（視認性重視）
        self.matched_color = QColor(144, 238, 144)  # ライトグリーン（照合済み）
        self.processing_color = QColor(255, 255, 153)  # 薄い黄色（処理中）
        self.processed_color = QColor(173, 216, 230)  # ライトブルー（処理済み）
        self.unprocessed_color = QColor(248, 248, 248)  # オフホワイト（未処理）

        # レイアウト設定
        self.setup_ui()

    def setup_ui(self):
        # メインレイアウト
        main_layout = QVBoxLayout(self)

        # 凡例エリア（色分けの説明）
        legend_frame = QFrame()
        legend_layout = QHBoxLayout(legend_frame)
        legend_layout.setContentsMargins(10, 5, 10, 5)
        main_layout.addWidget(legend_frame)

        legend_layout.addWidget(QLabel("🎨 色分け凡例:"))

        # 各状態の色見本を表示
        legend_items = [
            ("照合済み", self.matched_color),
            ("処理済み", self.processed_color),
            ("処理中", self.processing_color),
            ("未処理", self.unprocessed_color),
        ]

        for status, color in legend_items:
            color_label = QLabel(f" {status} ")
            color_label.setStyleSheet(
                f"""
                background-color: rgb({color.red()}, {color.green()}, {color.blue()});
                border: 1px solid #888;
                padding: 2px 8px;
                border-radius: 3px;
                font-weight: bold;
            """
            )
            legend_layout.addWidget(color_label)

        legend_layout.addStretch()

        # 検索フレーム
        search_frame = QFrame()
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(10, 5, 10, 5)
        main_layout.addWidget(search_frame)

        # 状態フィルタ
        search_layout.addWidget(QLabel("📊 状態:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(["すべて", "未処理", "処理中", "処理済", "照合済"])
        self.status_filter.setFixedWidth(100)
        self.status_filter.currentTextChanged.connect(self.filter_by_status)
        search_layout.addWidget(self.status_filter)

        search_layout.addWidget(QLabel("🔍 検索:"))
        self.search_entry = QLineEdit()
        self.search_entry.setFixedWidth(300)
        self.search_entry.setPlaceholderText("件名、案件名、支払い先で検索...")
        self.search_entry.returnPressed.connect(self.search_records)  # Enterキーで検索
        search_layout.addWidget(self.search_entry)

        search_button = QPushButton("検索")
        search_button.clicked.connect(self.search_records)
        search_layout.addWidget(search_button)

        reset_button = QPushButton("リセット")
        reset_button.clicked.connect(self.reset_search)
        search_layout.addWidget(reset_button)

        search_layout.addStretch()

        reload_button = QPushButton("📥 データ再読込")
        reload_button.clicked.connect(self.app.reload_data)
        search_layout.addWidget(reload_button)

        # 並べ替えフレーム
        sort_frame = QFrame()
        sort_layout = QHBoxLayout(sort_frame)
        sort_layout.setContentsMargins(10, 5, 10, 5)
        main_layout.addWidget(sort_frame)

        sort_layout.addWidget(QLabel("📊 並び順:"))

        sort_columns = [
            "件名",
            "案件名",
            "支払い先",
            "コード",
            "金額",
            "支払日",
            "状態",
        ]

        self.sort_column_combo = QComboBox()
        self.sort_column_combo.addItems(sort_columns)
        self.sort_column_combo.setCurrentText("支払日")
        sort_layout.addWidget(self.sort_column_combo)

        self.sort_order_combo = QComboBox()
        self.sort_order_combo.addItems(["降順", "昇順"])
        sort_layout.addWidget(self.sort_order_combo)

        apply_sort_button = QPushButton("適用")
        apply_sort_button.clicked.connect(self.apply_sort)
        sort_layout.addWidget(apply_sort_button)

        sort_layout.addStretch()

        self.csv_info_label = QLabel("")
        sort_layout.addWidget(self.csv_info_label)

        # ツリーウィジェットのフレーム
        tree_frame = QFrame()
        tree_layout = QVBoxLayout(tree_frame)
        tree_layout.setContentsMargins(10, 5, 10, 5)
        main_layout.addWidget(tree_frame)

        # テーブルタイトル
        table_title = QLabel("💰 支払い情報一覧")
        table_title.setFont(QFont("", 10, QFont.Bold))
        table_title.setStyleSheet("color: #2c3e50; margin-bottom: 5px;")
        tree_layout.addWidget(table_title)

        # ツリーウィジェットの作成
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(
            ["件名", "案件名", "支払い先", "コード", "金額", "支払日", "状態"]
        )
        tree_layout.addWidget(self.tree)

        # 列の設定
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)  # 件名
        self.tree.header().setSectionResizeMode(
            1, QHeaderView.ResizeToContents
        )  # 案件名
        self.tree.header().setSectionResizeMode(
            2, QHeaderView.ResizeToContents
        )  # 支払い先
        self.tree.header().setSectionResizeMode(
            3, QHeaderView.ResizeToContents
        )  # コード
        self.tree.header().setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 金額
        self.tree.header().setSectionResizeMode(
            5, QHeaderView.ResizeToContents
        )  # 支払日
        self.tree.header().setSectionResizeMode(6, QHeaderView.ResizeToContents)  # 状態

        # 複数選択を可能に
        self.tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        self.tree.setAlternatingRowColors(False)  # 交互背景色を無効化（色分けのため）

        # ヘッダークリックでソート機能（PyQt5対応版）
        self.tree.header().sectionClicked.connect(self.on_header_clicked)
        # PyQt5対応: setClickable → setSectionsClickable
        self.tree.header().setSectionsClickable(True)
        # PyQt5対応: setHighlightSections は存在しないので削除

        # 選択時イベント
        self.tree.itemSelectionChanged.connect(self.on_treeview_select)

        # 詳細フレーム
        detail_frame = QGroupBox("📋 詳細情報")
        detail_layout = QGridLayout(detail_frame)
        main_layout.addWidget(detail_frame)

        self.detail_labels = {}
        detail_fields = [
            "件名",
            "案件名",
            "支払い先",
            "コード",
            "金額",
            "支払日",
            "状態",
        ]

        for i, field in enumerate(detail_fields):
            row = i // 3
            col = i % 3 * 2

            detail_layout.addWidget(QLabel(f"{field}:"), row, col)

            value_label = QLabel("")
            value_label.setFixedWidth(150)
            value_label.setStyleSheet(
                "background-color: #f8f9fa; padding: 2px; border: 1px solid #dee2e6;"
            )
            detail_layout.addWidget(value_label, row, col + 1)

            self.detail_labels[field] = value_label

        # 状態変更ボタンフレーム
        status_button_frame = QFrame()
        status_button_layout = QHBoxLayout(status_button_frame)
        status_button_layout.setContentsMargins(10, 5, 10, 5)
        main_layout.addWidget(status_button_frame)

        # 状態変更ボタングループ
        status_group = QGroupBox("🔄 状態変更")
        status_group_layout = QHBoxLayout(status_group)
        status_button_layout.addWidget(status_group)

        unprocessed_button = QPushButton("⬜ 未処理に戻す")
        unprocessed_button.clicked.connect(self.mark_as_unprocessed)
        status_group_layout.addWidget(unprocessed_button)

        processed_button = QPushButton("✅ 処理済みにする")
        processed_button.clicked.connect(self.mark_as_processed)
        status_group_layout.addWidget(processed_button)

        # 照合ボタングループ
        match_group = QGroupBox("💰 照合操作")
        match_group_layout = QHBoxLayout(match_group)
        status_button_layout.addWidget(match_group)

        match_button = QPushButton("🔍 費用データと照合")
        match_button.clicked.connect(self.match_with_expenses)
        match_group_layout.addWidget(match_button)

    def get_color_for_status(self, status):
        """状態に応じた背景色を返す"""
        color_map = {
            "照合済": self.matched_color,
            "処理済": self.processed_color,
            "処理中": self.processing_color,
            "未処理": self.unprocessed_color,
        }
        return color_map.get(status, self.unprocessed_color)

    def apply_row_colors(self, item, status, column_count=7):
        """行に色を適用する共通メソッド"""
        background_color = self.get_color_for_status(status)
        brush = QBrush(background_color)
        
        # 明示的にテキスト色を黒に設定
        text_brush = QBrush(QColor(0, 0, 0))  # 黒色

        for i in range(column_count):
            item.setBackground(i, brush)
            item.setForeground(i, text_brush)  # テキスト色を明示的に設定
            # さらに確実にするため、データも設定
            item.setData(i, Qt.BackgroundRole, background_color)
            item.setData(i, Qt.ForegroundRole, QColor(0, 0, 0))

        # 照合済みの場合は太字
        if status == "照合済":
            font = QFont()
            font.setBold(True)
            for i in range(column_count):
                item.setFont(i, font)

    def filter_by_status(self):
        """状態でフィルタリング"""
        selected_status = self.status_filter.currentText()

        if selected_status == "すべて":
            self.refresh_data()
            return

        # 現在表示されている項目をフィルタリング
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            status = item.text(6)  # 状態列
            item.setHidden(status != selected_status)

        # 表示件数を更新
        visible_count = sum(
            1 for i in range(root.childCount()) if not root.child(i).isHidden()
        )
        self.app.status_label.setText(
            f"{selected_status}の支払いデータ: {visible_count}件"
        )

    def on_header_clicked(self, logical_index):
        """ヘッダークリック時のソート処理（改善版）"""
        # ヘッダー名を取得
        header_item = self.tree.headerItem()
        column_name = header_item.text(logical_index)

        # 同じ列を再度クリックした場合は昇順/降順を切り替え
        if self.sort_info["column"] == column_name:
            self.sort_info["reverse"] = not self.sort_info["reverse"]
        else:
            self.sort_info["reverse"] = False
            self.sort_info["column"] = column_name

        # ソート実行
        self.sort_tree_widget(column_name, self.sort_info["reverse"])

        # ソート状態を視覚的に表示（改善版）
        for i in range(self.tree.columnCount()):
            current_text = self.tree.headerItem().text(i)
            base_text = current_text.split(" ")[0]  # ▲▼を除いた部分

            if i == logical_index:
                # ソート対象の列には矢印を追加
                direction = " 🔽" if self.sort_info["reverse"] else " 🔼"
                self.tree.headerItem().setText(i, base_text + direction)
            else:
                # 他の列は元のテキストに戻す
                if " 🔼" in current_text or " 🔽" in current_text:
                    self.tree.headerItem().setText(i, base_text)

        # ソート方向を状態表示に反映
        direction_text = "降順" if self.sort_info["reverse"] else "昇順"
        self.app.status_label.setText(f"{column_name}で{direction_text}ソート中")

    def sort_tree_widget(self, column_name, reverse):
        """ツリーウィジェットのデータを指定された列で並べ替え（改善版）"""
        # ヘッダーのテキストからインデックスを取得
        column_index = -1
        for i in range(self.tree.columnCount()):
            header_text = self.tree.headerItem().text(i).split(" ")[0]
            if header_text == column_name:
                column_index = i
                break

        if column_index == -1:
            return  # 列が見つからない場合

        # 現在の項目をすべて取得
        items = []
        root = self.tree.invisibleRootItem()

        for i in range(root.childCount()):
            items.append(root.takeChild(0))

        # ソート関数（改善版）
        def get_sort_key(item):
            value = item.text(column_index)

            # 値のタイプに応じてソート
            if column_name in ["金額"]:
                # 金額は円マークとカンマを取り除いて数値としてソート
                try:
                    value = value.replace(",", "").replace("円", "").strip()
                    return float(value) if value else 0
                except (ValueError, TypeError):
                    return 0
            elif column_name in ["支払日"]:
                # 日付は文字列としてソート（YYYY-MM-DD形式想定）
                return value if value else "0000-00-00"
            elif column_name in ["状態"]:
                # 状態は優先順位でソート
                status_priority = {"未処理": 1, "処理中": 2, "処理済": 3, "照合済": 4}
                return status_priority.get(value, 0)
            else:
                # その他は文字列としてソート
                return value.lower() if value else ""

        # ソート実行
        try:
            items.sort(key=get_sort_key, reverse=reverse)
        except Exception as e:
            log_message(f"ソート中にエラー: {e}")
            # エラーが発生した場合は文字列ソートで再試行
            items.sort(
                key=lambda item: item.text(column_index).lower(), reverse=reverse
            )

        # ツリーに再追加
        for item in items:
            self.tree.addTopLevelItem(item)

    def refresh_data(self):
        """支払いデータを更新（改善版）"""
        # ツリーのクリア
        self.tree.clear()

        try:
            # データベースからデータを読み込み
            payment_rows, matched_count = self.db_manager.get_payment_data()

            # ツリーウィジェットにデータを追加
            for row in payment_rows:
                item = QTreeWidgetItem()

                # 値を設定
                item.setText(0, row[1])  # 件名
                item.setText(1, row[2])  # 案件名
                item.setText(2, row[3])  # 支払い先
                item.setText(3, row[4] if row[4] else "")  # 支払い先コード
                item.setText(4, format_amount(row[5]))  # 金額（整形）
                item.setText(5, row[6])  # 支払日
                item.setText(6, row[7])  # 状態

                # 状態に応じた背景色を適用
                status = row[7]
                self.apply_row_colors(item, status, 7)

                self.tree.addTopLevelItem(item)

            # 状態表示の更新（改善版）
            total_count = len(payment_rows)
            unprocessed_count = sum(1 for row in payment_rows if row[7] == "未処理")
            processing_count = sum(1 for row in payment_rows if row[7] == "処理中")
            processed_count = sum(1 for row in payment_rows if row[7] == "処理済")

            self.app.status_label.setText(
                f"支払いデータ: 全{total_count}件 "
                f"(未処理:{unprocessed_count}件, 処理中:{processing_count}件, "
                f"処理済:{processed_count}件, 照合済み:{matched_count}件)"
            )

            # 最終更新時刻の更新
            from datetime import datetime

            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.app.last_update_label.setText(f"最終更新: {current_time}")

            # 保存されているソート状態を適用
            if self.sort_info["column"]:
                self.sort_tree_widget(
                    self.sort_info["column"], self.sort_info["reverse"]
                )

                # ソート状態を視覚的に表示
                for i in range(self.tree.columnCount()):
                    header_text = self.tree.headerItem().text(i).split(" ")[0]
                    if header_text == self.sort_info["column"]:
                        direction = " 🔽" if self.sort_info["reverse"] else " 🔼"
                        self.tree.headerItem().setText(
                            i, self.sort_info["column"] + direction
                        )
                        break

            log_message("支払いデータの更新が完了しました")

        except Exception as e:
            log_message(f"支払いデータ読み込み中にエラーが発生: {e}")
            import traceback

            log_message(traceback.format_exc())
            self.app.status_label.setText(f"エラー: 支払いデータ読み込みに失敗しました")

    def on_treeview_select(self):
        """ツリーウィジェットの行選択時の処理（改善版）"""
        selected_items = self.tree.selectedItems()
        if not selected_items:
            # 選択がない場合は詳細をクリア
            for field, label in self.detail_labels.items():
                label.setText("")
            return

        # 選択項目の値を取得
        selected_item = selected_items[0]

        # 詳細情報を更新
        field_names = [
            "件名",
            "案件名",
            "支払い先",
            "コード",
            "金額",
            "支払日",
            "状態",
        ]
        for i, field in enumerate(field_names):
            if i < self.tree.columnCount():
                text = selected_item.text(i)
                self.detail_labels[field].setText(text)

                # 状態に応じて詳細ラベルの色も変更
                if field == "状態":
                    color = self.get_color_for_status(text)
                    self.detail_labels[field].setStyleSheet(
                        f"""background-color: rgb({color.red()}, {color.green()}, {color.blue()}); 
                        padding: 2px; border: 1px solid #dee2e6; font-weight: bold;"""
                    )
                else:
                    self.detail_labels[field].setStyleSheet(
                        "background-color: #f8f9fa; padding: 2px; border: 1px solid #dee2e6;"
                    )
            else:
                self.detail_labels[field].setText("")

    def mark_as_processed(self):
        """選択された支払いデータを「処理済み」に変更する"""
        selected_items = self.tree.selectedItems()
        if not selected_items:
            QMessageBox.information(
                self, "情報", "処理済みにする支払いデータを選択してください"
            )
            return

        # 確認ダイアログ
        if len(selected_items) == 1:
            confirm_msg = f"「{selected_items[0].text(0)}」を処理済みにしますか？"
        else:
            confirm_msg = f"{len(selected_items)}件のデータを処理済みにしますか？"

        reply = QMessageBox.question(
            self, "確認", confirm_msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
        )

        if reply != QMessageBox.Yes:
            return

        try:
            # 変更した件数
            count = 0

            # 各選択行を処理
            for item in selected_items:
                # 件名から対象レコードを特定する
                subject = item.text(0)
                payment_date = item.text(5)
                payee = item.text(2)

                # 対象レコードを更新
                count += self.db_manager.update_payment_status(
                    subject, payment_date, payee, "処理済"
                )

            # 状態表示の更新
            self.app.status_label.setText(
                f"{count}件の支払いデータを処理済みにしました"
            )

            # データを再表示
            self.refresh_data()

        except Exception as e:
            log_message(f"支払いデータの状態変更中にエラーが発生: {e}")
            QMessageBox.critical(
                self, "エラー", f"支払いデータの状態変更に失敗しました: {e}"
            )

    def mark_as_unprocessed(self):
        """選択された支払いデータを「未処理」に戻す"""
        selected_items = self.tree.selectedItems()
        if not selected_items:
            QMessageBox.information(
                self, "情報", "未処理に戻す支払いデータを選択してください"
            )
            return

        # 確認ダイアログ
        if len(selected_items) == 1:
            confirm_msg = f"「{selected_items[0].text(0)}」を未処理に戻しますか？"
        else:
            confirm_msg = f"{len(selected_items)}件のデータを未処理に戻しますか？"

        reply = QMessageBox.question(
            self, "確認", confirm_msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
        )

        if reply != QMessageBox.Yes:
            return

        try:
            # 変更した件数
            count = 0

            # 各選択行を処理
            for item in selected_items:
                # 件名から対象レコードを特定する
                subject = item.text(0)
                payment_date = item.text(5)
                payee = item.text(2)

                # 対象レコードを更新
                count += self.db_manager.update_payment_status(
                    subject, payment_date, payee, "未処理"
                )

            # 状態表示の更新
            self.app.status_label.setText(
                f"{count}件の支払いデータを未処理に戻しました"
            )

            # データを再表示
            self.refresh_data()

        except Exception as e:
            log_message(f"支払いデータの状態変更中にエラーが発生: {e}")
            QMessageBox.critical(
                self, "エラー", f"支払いデータの状態変更に失敗しました: {e}"
            )

    def apply_sort(self):
        """選択された列と順序で支払いデータを並べ替え"""
        column = self.sort_column_combo.currentText()
        order = self.sort_order_combo.currentText()

        # 並べ替え
        reverse = order == "降順"

        # ソート情報を更新
        self.sort_info["column"] = column
        self.sort_info["reverse"] = reverse

        # ソート実行
        self.sort_tree_widget(column, reverse)

        # ソート状態を視覚的に表示
        for i in range(self.tree.columnCount()):
            current_text = self.tree.headerItem().text(i)
            base_text = current_text.split(" ")[0]  # マークを削除
            self.tree.headerItem().setText(i, base_text)

        # ヘッダーのテキストからインデックスを取得
        for i in range(self.tree.columnCount()):
            if self.tree.headerItem().text(i) == column:
                direction = " 🔽" if reverse else " 🔼"
                self.tree.headerItem().setText(i, column + direction)
                break

        self.app.status_label.setText(
            f"支払いデータを{column}で{order}に並べ替えました"
        )

    def search_records(self):
        """支払いレコードの検索（改善版）"""
        search_term = self.search_entry.text().strip()
        if not search_term:
            self.refresh_data()
            return

        # ツリーのクリア
        self.tree.clear()

        try:
            # データベースから検索
            payment_rows, _ = self.db_manager.get_payment_data(search_term)

            # 検索結果をツリーウィジェットに追加
            for row in payment_rows:
                item = QTreeWidgetItem()

                # 値を設定
                item.setText(0, row[1])  # 件名
                item.setText(1, row[2])  # 案件名
                item.setText(2, row[3])  # 支払い先
                item.setText(3, row[4] if row[4] else "")  # 支払い先コード
                item.setText(4, format_amount(row[5]))  # 金額（整形）
                item.setText(5, row[6])  # 支払日
                item.setText(6, row[7])  # 状態

                # 状態に応じた背景色を適用
                status = row[7]
                self.apply_row_colors(item, status, 7)

                self.tree.addTopLevelItem(item)

            # 状態表示の更新
            self.app.status_label.setText(
                f"「{search_term}」の検索結果: {len(payment_rows)}件"
            )

        except Exception as e:
            log_message(f"支払いデータ検索中にエラーが発生: {e}")
            self.app.status_label.setText(f"エラー: 支払いデータ検索に失敗しました")

    def reset_search(self):
        """支払い検索をリセットしてすべてのデータを表示"""
        self.search_entry.clear()
        self.status_filter.setCurrentText("すべて")
        self.refresh_data()

    def match_with_expenses(self):
        """支払いテーブルと費用テーブルを照合する"""
        try:
            # 確認ダイアログ
            reply = QMessageBox.question(
                self,
                "確認",
                "支払いデータと費用データの照合を実行しますか？\n\n"
                "この処理により、金額・支払先コード・支払月が一致するデータが自動的に照合済みとしてマークされます。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )

            if reply != QMessageBox.Yes:
                return

            # 照合処理を実行
            self.app.status_label.setText("照合処理を実行中...")
            matched_count, not_matched_count = (
                self.db_manager.match_expenses_with_payments()
            )

            if matched_count == 0 and not_matched_count == 0:
                QMessageBox.information(self, "情報", "照合対象のデータがありません")
                return

            # データを更新表示
            self.refresh_data()  # 支払いデータを更新
            if hasattr(self.app, "expense_tab"):
                self.app.expense_tab.refresh_data()  # 費用データも更新

            # 結果メッセージ
            result_msg = f"照合処理完了\n\n✅ 照合成功: {matched_count}件\n❌ 照合失敗: {not_matched_count}件"

            self.app.status_label.setText(
                f"照合完了: {matched_count}件一致、{not_matched_count}件不一致"
            )

            QMessageBox.information(self, "照合完了", result_msg)

            log_message(
                f"支払いと費用の照合: {matched_count}件一致、{not_matched_count}件不一致"
            )

        except Exception as e:
            log_message(f"照合処理中にエラーが発生: {e}")
            import traceback

            log_message(traceback.format_exc())
            QMessageBox.critical(self, "エラー", f"照合処理に失敗しました: {e}")


# ファイル終了確認用のコメント - payment_tab.py完了
