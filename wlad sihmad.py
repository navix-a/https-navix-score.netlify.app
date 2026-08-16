import sys
import sqlite3
import os
import webbrowser
import urllib.parse
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QDialog, 
                             QVBoxLayout, QHBoxLayout, QFormLayout, QTableWidget, 
                             QTableWidgetItem, QLineEdit, QLabel, QPushButton, 
                             QMessageBox, QHeaderView, QScrollArea, QStackedWidget,
                             QGridLayout, QTextEdit, QFrame, QFileDialog)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QPainter, QColor, QBrush, QPen

# ==========================================
# 1. إعداد قاعدة البيانات وتحديث الجداول تلقائياً
# ==========================================
def init_db():
    conn = sqlite3.connect('epicerie.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL,
            image_path TEXT DEFAULT ''
        )
    ''')
    
    try:
        cursor.execute("ALTER TABLE products ADD COLUMN image_path TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT,
            client_phone TEXT,
            client_address TEXT,
            total REAL,
            status TEXT DEFAULT 'En attente',
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        default_products = [
            ('101', 'زيت لوحة 1L', 20.00, 50, ''),
            ('102', 'ماء جافيل أتاك', 6.00, 40, ''),
            ('103', 'سكّر قالب (2kg)', 13.00, 60, ''),
            ('104', 'أتاي السبع', 12.00, 45, ''),
            ('105', 'تيد غسيل 500g', 10.00, 30, ''),
            ('106', 'بيمو هنريس', 2.00, 100, ''),
            ('107', 'حليب السنترال 1L', 3.50, 80, ''),
            ('108', 'دانون فواكه', 2.50, 60, ''),
            ('109', 'زبدة بدوية 250g', 15.00, 25, '')
        ]
        cursor.executemany("INSERT INTO products (barcode, name, price, stock, image_path) VALUES (?, ?, ?, ?, ?)", default_products)
        
    conn.commit()
    conn.close()

# ==========================================
# 2. رسم اللوغو وصور تعبيرية
# ==========================================
def create_store_logo(size=80):
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    painter.setBrush(QBrush(QColor("#2563eb")))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(0, 0, size, size, 16, 16)
    
    scale = size / 80.0
    painter.setPen(QPen(QColor("white"), int(4.5 * scale), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(int(22 * scale), int(30 * scale), int(32 * scale), int(30 * scale))
    painter.drawLine(int(32 * scale), int(30 * scale), int(40 * scale), int(54 * scale))
    painter.drawLine(int(40 * scale), int(54 * scale), int(62 * scale), int(54 * scale))
    painter.drawLine(int(62 * scale), int(54 * scale), int(67 * scale), int(36 * scale))
    painter.drawLine(int(67 * scale), int(36 * scale), int(30 * scale), int(36 * scale))
    
    painter.setBrush(QBrush(QColor("white")))
    painter.drawEllipse(int(40 * scale), int(58 * scale), int(6 * scale), int(6 * scale))
    painter.drawEllipse(int(56 * scale), int(58 * scale), int(6 * scale), int(6 * scale))
    
    painter.end()
    return pixmap

def create_placeholder_image(name, size=80):
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor("#e2e8f0"))
    painter = QPainter(pixmap)
    painter.setPen(QColor("#475569"))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, name[:2])
    painter.end()
    return pixmap

# ==========================================
# 3. واجهة الترحيب الأولى (Welcome Screen)
# ==========================================
class WelcomeScreen(QWidget):
    def __init__(self, start_callback):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        logo = QLabel()
        logo.setPixmap(create_store_logo(130))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo)
        
        layout.addSpacing(20)
        
        title = QLabel("مرحباً بكم في متجر ولاد سي أحمد")
        title.setStyleSheet("font-size: 36px; font-weight: bold; color: #1e293b;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("اختر سلعك المفضلة وسنوصلها لك حتى باب المنزل 🛵")
        subtitle.setStyleSheet("font-size: 18px; color: #64748b; margin-top: 5px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        layout.addSpacing(35)
        
        btn_start = QPushButton("ابدأ الطلب الآن 🛒")
        btn_start.setFixedWidth(280)
        btn_start.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                font-size: 20px;
                font-weight: bold;
                padding: 15px;
                border-radius: 10px;
                border: none;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        btn_start.clicked.connect(start_callback)
        layout.addWidget(btn_start, alignment=Qt.AlignmentFlag.AlignCenter)

# ==========================================
# 4. نافذة إدخال عنوان التوصيل للزبون
# ==========================================
class DeliveryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("تأكيد طلب التوصيل")
        self.setFixedSize(400, 350)
        self.setStyleSheet("""
            QDialog { background-color: #ffffff; color: #1e293b; }
            QLabel { color: #334155; font-size: 14px; font-weight: bold; }
            QLineEdit, QTextEdit { 
                background-color: #f8fafc; 
                border: 1px solid #cbd5e1; 
                border-radius: 8px; 
                color: #0f172a; 
                padding: 10px;
                font-size: 14px;
            }
            QLineEdit:focus, QTextEdit:focus { border: 1px solid #2563eb; }
            QPushButton {
                background-color: #2563eb;
                color: white;
                font-size: 16px;
                font-weight: bold;
                border-radius: 8px;
                padding: 12px;
                border: none;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        header_title = QLabel("معلومات التوصيل للدار 🛵")
        header_title.setStyleSheet("font-size: 18px; color: #2563eb; margin-bottom: 10px;")
        layout.addWidget(header_title, alignment=Qt.AlignmentFlag.AlignCenter)

        form_layout = QFormLayout()
        self.name_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.address_input = QTextEdit()
        self.address_input.setMaximumHeight(80)

        form_layout.addRow(QLabel("الاسم الكامل:"), self.name_input)
        form_layout.addRow(QLabel("رقم الهاتف:"), self.phone_input)
        form_layout.addRow(QLabel("عنوان التوصيل:"), self.address_input)

        layout.addLayout(form_layout)

        btn_confirm = QPushButton("تأكيد الطلب 🚀")
        btn_confirm.clicked.connect(self.accept)
        layout.addWidget(btn_confirm)

# ==========================================
# 5. شاشة الطلب للزبون (Kiosk Screen)
# ==========================================
class CustomerKioskWidget(QWidget):
    def __init__(self, open_stock_callback, back_callback):
        super().__init__()
        self.cart = {}
        self.open_stock_callback = open_stock_callback
        self.back_callback = back_callback
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 8px 15px;")
        header_layout = QHBoxLayout(header_frame)

        btn_back = QPushButton("⬅️ الواجهة الرئيسية")
        btn_back.setStyleSheet("""
            QPushButton {
                background-color: #f1f5f9; color: #334155; font-size: 14px; 
                font-weight: bold; padding: 8px 14px; border-radius: 8px; border: 1px solid #cbd5e1;
            }
            QPushButton:hover { background-color: #e2e8f0; }
        """)
        btn_back.clicked.connect(self.back_callback)
        header_layout.addWidget(btn_back)

        logo = QLabel()
        logo.setPixmap(create_store_logo(55))
        header_layout.addWidget(logo)

        store_title = QLabel("متجر ولاد سي أحمد")
        store_title.setStyleSheet("font-size: 26px; font-weight: 900; color: #2563eb;")
        header_layout.addWidget(store_title)

        header_layout.addStretch()

        btn_admin = QPushButton("⚙️ إدارة الستوك")
        btn_admin.setStyleSheet("""
            QPushButton {
                background-color: #0f172a; color: white; font-size: 14px; 
                font-weight: bold; padding: 10px 16px; border-radius: 8px; border: none;
            }
            QPushButton:hover { background-color: #334155; }
        """)
        btn_admin.clicked.connect(self.open_stock_callback)
        header_layout.addWidget(btn_admin)

        main_layout.addWidget(header_frame)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.products_container = QWidget()
        self.grid = QGridLayout(self.products_container)
        self.grid.setSpacing(15)
        scroll.setWidget(self.products_container)

        content_layout.addWidget(scroll, 2)

        cart_frame = QFrame()
        cart_frame.setStyleSheet("background-color: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 15px;")
        cart_layout = QVBoxLayout(cart_frame)

        cart_title = QLabel("سلة الشراء 🛒")
        cart_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #0f172a; margin-bottom: 5px;")
        cart_layout.addWidget(cart_title)

        self.cart_table = QTableWidget(0, 3)
        self.cart_table.setHorizontalHeaderLabels(["المنتج", "الكمية", "المجموع"])
        self.cart_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.cart_table.setStyleSheet("""
            QTableWidget { background-color: #f8fafc; color: #0f172a; gridline-color: #e2e8f0; border: 1px solid #cbd5e1; border-radius: 8px; }
            QHeaderView::section { background-color: #e2e8f0; color: #1e293b; font-weight: bold; border: none; padding: 6px; }
        """)
        cart_layout.addWidget(self.cart_table)

        self.total_label = QLabel("المجموع: 0.00 DH")
        self.total_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #16a34a; margin: 10px 0;")
        cart_layout.addWidget(self.total_label)

        btn_order = QPushButton("طلب التوصيل للمنزل 🛵")
        btn_order.setStyleSheet("""
            QPushButton {
                background-color: #16a34a; color: white; font-size: 18px; 
                font-weight: bold; padding: 14px; border-radius: 8px; border: none;
            }
            QPushButton:hover { background-color: #15803d; }
        """)
        btn_order.clicked.connect(self.submit_order)
        cart_layout.addWidget(btn_order)

        content_layout.addWidget(cart_frame, 1)
        main_layout.addLayout(content_layout)

        self.reload_products()

    def reload_products(self):
        for i in reversed(range(self.grid.count())): 
            self.grid.itemAt(i).widget().setParent(None)

        conn = sqlite3.connect('epicerie.db')
        cursor = conn.cursor()
        cursor.execute("SELECT barcode, name, price, stock, image_path FROM products WHERE stock > 0")
        products = cursor.fetchall()
        conn.close()

        row, col = 0, 0
        for barcode, name, price, stock, img_path in products:
            card = QFrame()
            card.setStyleSheet("""
                QFrame {
                    background-color: #ffffff;
                    border: 1px solid #e2e8f0;
                    border-radius: 12px;
                    padding: 10px;
                }
                QFrame:hover { border: 1px solid #2563eb; }
            """)
            card_layout = QVBoxLayout(card)

            img_label = QLabel()
            img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if img_path and os.path.exists(img_path):
                pixmap = QPixmap(img_path).scaled(90, 90, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            else:
                pixmap = create_placeholder_image(name, 90)
            img_label.setPixmap(pixmap)

            p_name = QLabel(f"<b>{name}</b>")
            p_name.setStyleSheet("font-size: 16px; color: #0f172a; border: none;")
            
            p_price = QLabel(f"{price:.2f} DH")
            p_price.setStyleSheet("font-size: 15px; color: #2563eb; font-weight: bold; border: none;")
            
            p_stock = QLabel(f"المتوفر: {stock}")
            p_stock.setStyleSheet("font-size: 12px; color: #64748b; border: none;")

            btn_add = QPushButton("إضافة للسلة ➕")
            btn_add.setStyleSheet("""
                QPushButton {
                    background-color: #f1f5f9; color: #1e293b; border: 1px solid #cbd5e1;
                    border-radius: 6px; padding: 8px; font-weight: bold;
                }
                QPushButton:hover { background-color: #2563eb; color: white; border: none; }
            """)
            btn_add.clicked.connect(lambda _, b=barcode, n=name, p=price, s=stock: self.add_to_cart(b, n, p, s))

            card_layout.addWidget(img_label)
            card_layout.addWidget(p_name)
            card_layout.addWidget(p_price)
            card_layout.addWidget(p_stock)
            card_layout.addWidget(btn_add)

            self.grid.addWidget(card, row, col)
            col += 1
            if col > 2:
                col = 0
                row += 1

    def add_to_cart(self, barcode, name, price, max_stock):
        if barcode in self.cart:
            if self.cart[barcode]['qty'] + 1 > max_stock:
                QMessageBox.warning(self, "تنبيه", "وصلت للحد الأقصى المتوفر في الستوك!")
                return
            self.cart[barcode]['qty'] += 1
        else:
            self.cart[barcode] = {'name': name, 'price': price, 'qty': 1, 'max_stock': max_stock}
        
        self.update_cart_display()

    def update_cart_display(self):
        self.cart_table.setRowCount(0)
        total = 0
        for barcode, item in self.cart.items():
            row_idx = self.cart_table.rowCount()
            item_total = item['price'] * item['qty']
            total += item_total

            self.cart_table.insertRow(row_idx)
            self.cart_table.setItem(row_idx, 0, QTableWidgetItem(item['name']))
            self.cart_table.setItem(row_idx, 1, QTableWidgetItem(str(item['qty'])))
            self.cart_table.setItem(row_idx, 2, QTableWidgetItem(f"{item_total:.2f} DH"))

        self.total_label.setText(f"المجموع: {total:.2f} DH")

    def submit_order(self):
        if not self.cart:
            QMessageBox.warning(self, "تنبيه", "السلة فارغة!")
            return

        dialog = DeliveryDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = dialog.name_input.text().strip()
            phone = dialog.phone_input.text().strip()
            address = dialog.address_input.toPlainText().strip()

            if not name or not phone or not address:
                QMessageBox.warning(self, "تنبيه", "يرجى ملء كافة معلومات التوصيل!")
                return

            total = sum(item['price'] * item['qty'] for item in self.cart.values())

            # 1. حفظ الطلبية في قاعدة البيانات
            conn = sqlite3.connect('epicerie.db')
            cursor = conn.cursor()

            cursor.execute("INSERT INTO orders (client_name, client_phone, client_address, total) VALUES (?, ?, ?, ?)",
                           (name, phone, address, total))

            for barcode, item in self.cart.items():
                cursor.execute("UPDATE products SET stock = stock - ? WHERE barcode = ?", (item['qty'], barcode))

            conn.commit()
            conn.close()

            # 2. إعداد تفاصيل الطلب لإرسالها عبر WhatsApp
            my_phone = "212667903785" # رقم هاتفك برمز المغرب
            
            items_list = ""
            for item in self.cart.values():
                items_list += f"- {item['name']} (الكمية: {item['qty']}) = {item['price'] * item['qty']:.2f} DH\n"

            msg = (f"🛍️ *طلب جديد من المتجر*\n\n"
                   f"👤 *اسم الزبون:* {name}\n"
                   f"📞 *الهاتف:* {phone}\n"
                   f"📍 *العنوان:* {address}\n\n"
                   f"📋 *المنتجات:*\n{items_list}\n"
                   f"💰 *المجموع الإجمالي:* {total:.2f} DH")

            # فتح رابط WhatsApp
            encoded_msg = urllib.parse.quote(msg)
            whatsapp_url = f"https://wa.me/{my_phone}?text={encoded_msg}"
            webbrowser.open(whatsapp_url)

            QMessageBox.information(self, "نجاح", f"شكراً لك {name}!\nتم تسجيل طلبك وفتح الواتساب لإرسال التاصيل.")
            self.cart.clear()
            self.update_cart_display()
            self.reload_products()

# ==========================================
# 6. نافذة إدارة الستوك
# ==========================================
class StockManagerDialog(QDialog):
    def __init__(self, parent=None, reload_callback=None):
        super().__init__(parent)
        self.reload_callback = reload_callback
        self.image_path = ""
        self.setWindowTitle("إدارة الستوك - متجر ولاد سي أحمد")
        self.setGeometry(150, 150, 850, 500)
        self.setStyleSheet("""
            QDialog { background-color: #ffffff; color: #0f172a; }
            QLabel { color: #334155; font-size: 13px; }
            QLineEdit { background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 6px; color: #0f172a; padding: 8px; }
            QTableWidget { background-color: #f8fafc; color: #0f172a; gridline-color: #e2e8f0; border: 1px solid #cbd5e1; }
            QHeaderView::section { background-color: #e2e8f0; color: #1e293b; font-weight: bold; }
        """)
        self.init_ui()
        self.load_products()

    def init_ui(self):
        layout = QHBoxLayout(self)

        form_layout = QFormLayout()
        self.barcode_input = QLineEdit()
        self.name_input = QLineEdit()
        self.price_input = QLineEdit()
        self.stock_input = QLineEdit()
        
        btn_img = QPushButton("اختر صورة للسلعة 🖼️")
        btn_img.setStyleSheet("background-color: #e2e8f0; padding: 6px; border-radius: 4px;")
        btn_img.clicked.connect(self.select_image)

        form_layout.addRow(QLabel("<b>البارشود:</b>"), self.barcode_input)
        form_layout.addRow(QLabel("<b>اسم المنتج:</b>"), self.name_input)
        form_layout.addRow(QLabel("<b>الثمن (DH):</b>"), self.price_input)
        form_layout.addRow(QLabel("<b>الكمية (الستوك):</b>"), self.stock_input)
        form_layout.addRow(QLabel("<b>صورة المنتج:</b>"), btn_img)

        btn_add = QPushButton("إضافة / تحديث المنتج")
        btn_add.setStyleSheet("background-color: #2563eb; color: white; padding: 10px; font-weight: bold; border-radius: 6px; border: none;")
        btn_add.clicked.connect(self.save_product)

        btn_clear = QPushButton("مسح الخانات")
        btn_clear.setStyleSheet("background-color: #94a3b8; color: white; padding: 8px; border-radius: 6px; border: none;")
        btn_clear.clicked.connect(self.clear_inputs)

        btn_delete = QPushButton("حذف المنتج")
        btn_delete.setStyleSheet("background-color: #ef4444; color: white; padding: 8px; border-radius: 6px; border: none;")
        btn_delete.clicked.connect(self.delete_product)

        form_layout.addRow(btn_add)
        form_layout.addRow(btn_clear)
        form_layout.addRow(btn_delete)

        layout.addLayout(form_layout, 1)

        right_layout = QVBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("ابحث بالاسم أو البارشود...")
        self.search_input.textChanged.connect(self.search_product)
        right_layout.addWidget(self.search_input)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["البارشود", "الاسم", "الثمن", "الستوك"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.cellClicked.connect(self.select_product_from_table)
        right_layout.addWidget(self.table)

        layout.addLayout(right_layout, 2)

    def select_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "اختر صورة للمنتج", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            self.image_path = file_path

    def load_products(self, query="SELECT barcode, name, price, stock FROM products"):
        conn = sqlite3.connect('epicerie.db')
        cursor = conn.cursor()
        cursor.execute(query)
        products = cursor.fetchall()
        conn.close()

        self.table.setRowCount(0)
        for row_data in products:
            row_idx = self.table.rowCount()
            self.table.insertRow(row_idx)
            for col_idx, value in enumerate(row_data):
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(str(value)))

    def save_product(self):
        barcode = self.barcode_input.text().strip()
        name = self.name_input.text().strip()
        price = self.price_input.text().strip()
        stock = self.stock_input.text().strip()

        if not barcode or not name or not price or not stock:
            QMessageBox.warning(self, "تنبيه", "يرجى ملء جميع الخانات!")
            return

        try:
            price_val = float(price)
            stock_val = int(stock)
        except ValueError:
            QMessageBox.warning(self, "خطأ", "الثمن والستوك يجب أن يكونا أرقاماً!")
            return

        conn = sqlite3.connect('epicerie.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO products (barcode, name, price, stock, image_path)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(barcode) DO UPDATE SET
                name=excluded.name,
                price=excluded.price,
                stock=excluded.stock,
                image_path=excluded.image_path
        ''', (barcode, name, price_val, stock_val, self.image_path))
        conn.commit()
        conn.close()

        QMessageBox.information(self, "نجاح", "تم حفظ المنتج بنجاح!")
        self.clear_inputs()
        self.load_products()
        if self.reload_callback:
            self.reload_callback()

    def select_product_from_table(self, row, column):
        self.barcode_input.setText(self.table.item(row, 0).text())
        self.name_input.setText(self.table.item(row, 1).text())
        self.price_input.setText(self.table.item(row, 2).text())
        self.stock_input.setText(self.table.item(row, 3).text())

    def search_product(self):
        text = self.search_input.text().strip()
        if not text:
            self.load_products()
            return

        conn = sqlite3.connect('epicerie.db')
        cursor = conn.cursor()
        cursor.execute("SELECT barcode, name, price, stock FROM products WHERE barcode LIKE ? OR name LIKE ?", 
                       (f'%{text}%', f'%{text}%'))
        products = cursor.fetchall()
        conn.close()

        self.table.setRowCount(0)
        for row_data in products:
            row_idx = self.table.rowCount()
            self.table.insertRow(row_idx)
            for col_idx, value in enumerate(row_data):
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(str(value)))

    def delete_product(self):
        barcode = self.barcode_input.text().strip()
        if not barcode:
            QMessageBox.warning(self, "تنبيه", "حدد منتجاً للحذف أولاً.")
            return

        reply = QMessageBox.question(self, 'تأكيد الحذف', 'هل أنت تأكد من حذف المنتج؟',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            conn = sqlite3.connect('epicerie.db')
            cursor = conn.cursor()
            cursor.execute("DELETE FROM products WHERE barcode = ?", (barcode,))
            conn.commit()
            conn.close()
            self.clear_inputs()
            self.load_products()
            if self.reload_callback:
                self.reload_callback()

    def clear_inputs(self):
        self.barcode_input.clear()
        self.name_input.clear()
        self.price_input.clear()
        self.stock_input.clear()
        self.image_path = ""

# ==========================================
# 7. النافذة الرئيسية لتشغيل الجهاز
# ==========================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("متجر ولاد سي أحمد")
        self.setGeometry(100, 100, 1050, 680)
        self.setStyleSheet("QMainWindow { background-color: #f8fafc; }")
        
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        self.welcome_screen = WelcomeScreen(self.show_kiosk)
        self.kiosk_screen = CustomerKioskWidget(self.open_stock, self.show_welcome)
        
        self.stacked_widget.addWidget(self.welcome_screen)
        self.stacked_widget.addWidget(self.kiosk_screen)
        
        self.stacked_widget.setCurrentWidget(self.welcome_screen)

    def show_kiosk(self):
        self.stacked_widget.setCurrentWidget(self.kiosk_screen)

    def show_welcome(self):
        self.stacked_widget.setCurrentWidget(self.welcome_screen)

    def open_stock(self):
        dialog = StockManagerDialog(self, reload_callback=self.kiosk_screen.reload_products)
        dialog.exec()

if __name__ == '__main__':
    init_db()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
