from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, 
    QLineEdit, QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QDialog, QFormLayout, QDialogButtonBox,
    QTabWidget
)
from PySide6.QtCore import Qt, Signal
from database.connection import get_session
from database.models import Inventory, StockTransaction
import datetime

class InventoryPanel(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.tabs = QTabWidget()
        
        # 1. Catalog Tab
        self.catalog_tab = QWidget()
        self.init_catalog_tab()
        self.tabs.addTab(self.catalog_tab, "Current Stock")
        
        # 2. Transactions Log Tab
        self.tx_tab = QWidget()
        self.init_tx_tab()
        self.tabs.addTab(self.tx_tab, "Stock Ledger Logs")
        
        layout.addWidget(self.tabs)
        
    # --- Catalog ---
    def init_catalog_tab(self):
        tab_layout = QVBoxLayout(self.catalog_tab)
        tab_layout.setContentsMargins(15, 15, 15, 15)
        tab_layout.setSpacing(15)
        
        actions = QHBoxLayout()
        self.search_item_input = QLineEdit()
        self.search_item_input.setPlaceholderText("Search inventory by item name...")
        self.search_item_input.textChanged.connect(self.load_catalog)
        actions.addWidget(self.search_item_input, stretch=3)
        
        register_btn = QPushButton("Register Item")
        register_btn.setObjectName("secondary_btn")
        register_btn.clicked.connect(self.open_register_dialog)
        actions.addWidget(register_btn)
        
        tx_btn = QPushButton("Record Stock IN/OUT")
        tx_btn.setObjectName("primary_btn")
        tx_btn.clicked.connect(self.open_tx_dialog)
        actions.addWidget(tx_btn)
        
        tab_layout.addLayout(actions)
        
        self.catalog_table = QTableWidget()
        self.catalog_table.setColumnCount(7)
        self.catalog_table.setHorizontalHeaderLabels([
            "Item ID", "Item Name", "Category", "Quantity Available", "Unit", "Condition", "Location"
        ])
        self.catalog_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.catalog_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        tab_layout.addWidget(self.catalog_table)
        self.load_catalog()
        
    def load_catalog(self):
        self.catalog_table.setRowCount(0)
        session = get_session()
        try:
            query = session.query(Inventory)
            search_text = self.search_item_input.text().strip()
            if search_text:
                query = query.filter(Inventory.item_name.ilike(f"%{search_text}%"))
                
            items = query.order_by(Inventory.item_name.asc()).all()
            self.catalog_table.setRowCount(len(items))
            
            for i, item in enumerate(items):
                self.catalog_table.setItem(i, 0, QTableWidgetItem(str(item.id)))
                self.catalog_table.setItem(i, 1, QTableWidgetItem(item.item_name))
                self.catalog_table.setItem(i, 2, QTableWidgetItem(item.category))
                self.catalog_table.setItem(i, 3, QTableWidgetItem(f"{item.available_quantity} / {item.total_quantity}"))
                self.catalog_table.setItem(i, 4, QTableWidgetItem(item.unit))
                self.catalog_table.setItem(i, 5, QTableWidgetItem(item.condition or "Good"))
                self.catalog_table.setItem(i, 6, QTableWidgetItem(item.location or "N/A"))
        except Exception as e:
            print(f"Error loading catalog: {e}")
        finally:
            session.close()

    def open_register_dialog(self):
        dialog = RegisterItemDialog(self)
        dialog.data_changed.connect(self.load_catalog)
        dialog.exec()
        
    def open_tx_dialog(self):
        dialog = RecordStockTransactionDialog(self.user, self)
        dialog.data_changed.connect(self.load_catalog)
        dialog.data_changed.connect(self.load_tx_log)
        dialog.exec()

    # --- Transactions Log ---
    def init_tx_tab(self):
        tab_layout = QVBoxLayout(self.tx_tab)
        tab_layout.setContentsMargins(15, 15, 15, 15)
        tab_layout.setSpacing(15)
        
        self.tx_table = QTableWidget()
        self.tx_table.setColumnCount(7)
        self.tx_table.setHorizontalHeaderLabels([
            "Tx ID", "Item Name", "Tx Type", "Quantity", "Date Recorded", "Reference", "Supplier Source"
        ])
        self.tx_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tx_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        tab_layout.addWidget(self.tx_table)
        self.load_tx_log()
        
    def load_tx_log(self):
        self.tx_table.setRowCount(0)
        session = get_session()
        try:
            txs = session.query(StockTransaction).order_by(StockTransaction.transaction_date.desc()).all()
            self.tx_table.setRowCount(len(txs))
            for i, tx in enumerate(txs):
                self.tx_table.setItem(i, 0, QTableWidgetItem(str(tx.id)))
                self.tx_table.setItem(i, 1, QTableWidgetItem(tx.inventory_item.item_name))
                self.tx_table.setItem(i, 2, QTableWidgetItem(tx.transaction_type))
                self.tx_table.setItem(i, 3, QTableWidgetItem(str(tx.quantity)))
                self.tx_table.setItem(i, 4, QTableWidgetItem(tx.transaction_date.strftime("%Y-%m-%d %H:%M")))
                self.tx_table.setItem(i, 5, QTableWidgetItem(tx.reference or "N/A"))
                self.tx_table.setItem(i, 6, QTableWidgetItem(tx.supplier_name or "N/A"))
        except Exception as e:
            print(f"Error loading transactions: {e}")
        finally:
            session.close()
            
    def refresh(self):
        self.load_catalog()
        self.load_tx_log()

class RegisterItemDialog(QDialog):
    data_changed = Signal()
    
    def __init__(self, parent_widget=None):
        super().__init__(parent_widget)
        self.setWindowTitle("Register Inventory Item")
        self.setMinimumWidth(320)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.name_input = QLineEdit()
        self.cat_combo = QComboBox()
        self.cat_combo.addItems(["Asset", "Supply"])
        self.desc_input = QLineEdit()
        self.unit_input = QLineEdit("pcs")
        self.cond_combo = QComboBox()
        self.cond_combo.addItems(["Good", "Needs Repair", "Damaged"])
        self.loc_input = QLineEdit()
        
        form_layout.addRow("Item Name:", self.name_input)
        form_layout.addRow("Category:", self.cat_combo)
        form_layout.addRow("Description:", self.desc_input)
        form_layout.addRow("Counting Unit:", self.unit_input)
        form_layout.addRow("Initial Condition:", self.cond_combo)
        form_layout.addRow("Store Location:", self.loc_input)
        
        layout.addLayout(form_layout)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.save_item)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)
        
    def save_item(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Item name is required.")
            return
            
        session = get_session()
        try:
            item = Inventory(
                item_name=name,
                category=self.cat_combo.currentText(),
                description=self.desc_input.text().strip() or None,
                total_quantity=0,
                available_quantity=0,
                unit=self.unit_input.text().strip(),
                condition=self.cond_combo.currentText(),
                location=self.loc_input.text().strip() or None
            )
            session.add(item)
            session.commit()
            
            QMessageBox.information(self, "Success", f"Item '{name}' registered in catalogue.")
            self.data_changed.emit()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save item: {e}")
        finally:
            session.close()

class RecordStockTransactionDialog(QDialog):
    data_changed = Signal()
    
    def __init__(self, user, parent_widget=None):
        super().__init__(parent_widget)
        self.user = user
        self.setWindowTitle("Record Stock Transaction")
        self.setMinimumWidth(360)
        self.init_ui()
        self.load_items()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.item_combo = QComboBox()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["IN", "OUT"])
        self.qty_input = QLineEdit()
        self.ref_input = QLineEdit()
        self.supplier_input = QLineEdit()
        
        form_layout.addRow("Select Item:", self.item_combo)
        form_layout.addRow("Transaction Type:", self.type_combo)
        form_layout.addRow("Quantity Change:", self.qty_input)
        form_layout.addRow("Reference/Invoice No:", self.ref_input)
        form_layout.addRow("Supplier (for IN):", self.supplier_input)
        
        layout.addLayout(form_layout)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.save_transaction)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)
        
    def load_items(self):
        session = get_session()
        try:
            items = session.query(Inventory).all()
            for i in items:
                self.item_combo.addItem(f"{i.item_name} ({i.available_quantity} avail)", i.id)
        except Exception as e:
            print(f"Error loading items: {e}")
        finally:
            session.close()
            
    def save_transaction(self):
        item_id = self.item_combo.currentData()
        tx_type = self.type_combo.currentText()
        try:
            qty = int(self.qty_input.text().strip() or "0")
        except ValueError:
            QMessageBox.warning(self, "Validation Error", "Invalid quantity number.")
            return
            
        if not item_id or qty <= 0:
            QMessageBox.warning(self, "Validation Error", "Please select an item and type a positive quantity.")
            return
            
        session = get_session()
        try:
            item = session.query(Inventory).filter(Inventory.id == item_id).first()
            if item:
                # Update quantities based on IN/OUT
                if tx_type == "IN":
                    item.total_quantity += qty
                    item.available_quantity += qty
                else:  # OUT
                    if qty > item.available_quantity:
                        QMessageBox.warning(self, "Insufficient Stock", f"Only {item.available_quantity} copies are currently available in store.")
                        return
                    item.available_quantity -= qty
                    # Depending on policy, total_quantity might remain the same (assets in use)
                    # or decrement for consumable supplies:
                    if item.category == "Supply":
                        item.total_quantity -= qty
                
                staff_id = self.user.staff_profile.id if self.user.staff_profile else None
                tx = StockTransaction(
                    inventory_id=item_id,
                    transaction_type=tx_type,
                    quantity=qty,
                    reference=self.ref_input.text().strip() or None,
                    supplier_name=self.supplier_input.text().strip() if tx_type == "IN" else None,
                    staff_id=staff_id
                )
                session.add(tx)
                session.commit()
                
                QMessageBox.information(self, "Success", "Stock transaction recorded.")
                self.data_changed.emit()
                self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to record transaction: {e}")
        finally:
            session.close()
