from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidgetItem, QMessageBox, QColorDialog, \
    QFileDialog, QGridLayout, QLabel, QDialog, QPushButton
from PyQt5.QtGui import QColor, QPixmap
from PyQt5.QtCore import QEvent
from project import Ui_Book_Reader
import webbrowser
import sqlite3
import re
import sys


def sqlite_like(template_, value_):  # эта и последующие функции (до следующего комментария)
    # служат для обеспечения работоспособности функций LIKE, UPPER, LOWER языка SQL для русского текста
    return sqlite_like_escape(template_, value_, None)


def sqlite_like_escape(template_, value_, escape_):
    re_ = re.compile(template_.lower().
                     replace(".", "\\.").replace("^", "\\^").replace("$", "\\$").
                     replace("*", "\\*").replace("+", "\\+").replace("?", "\\?").
                     replace("{", "\\{").replace("}", "\\}").replace("(", "\\(").
                     replace(")", "\\)").replace("[", "\\[").replace("]", "\\]").
                     replace("_", ".").replace("%", ".*?"))
    return re_.match(value_.lower()) is not None


def sqlite_nocase_collation(value1_, value2_):
    return (value1_.encode('utf-8').lower() < value2_.encode('utf-8').lower()) - (
            value1_.encode('utf-8').lower() > value2_.encode('utf-8').lower())


class MyWidget(QMainWindow, Ui_Book_Reader):  # основной класс
    def __init__(self):  # инициализация объекта класса. По факту начальная настройка приложения
        super().__init__()
        self.setupUi(self)
        # настройка "растягиваемого" экрана
        self.setCentralWidget(self.centralwidget)
        self.grid1 = QGridLayout(self.centralwidget)
        self.grid1.addWidget(self.tabWidget)
        self.tabSelect.setLayout(self.gridLayout)
        self.tabAdd.setLayout(self.gridLayout_7)
        self.tabText.setLayout(self.gridLayout_6)
        # подкючение к бд
        self.con = sqlite3.connect("articles.db")
        # установка начального цвета фона во вкладке чтения
        self.textBrowser.setTextColor(QColor('#000000'))
        # добавление строк для поиска по жанру
        genres = self.con.execute('select genre from Genre').fetchall()
        for el in genres:
            self.genre_comboBox.addItem(str(el[0]))
        # вставка картинки (на которую можно нажимать)
        self.pixmap = QPixmap('texts/preview.jpg')
        self.label_4.setPixmap(self.pixmap)
        self.label_4.installEventFilter(self)
        # подключение элементов к функциям
        self.load_text_button.clicked.connect(self.load_text)
        self.delete_button.clicked.connect(self.delete_files)
        self.background_color_button.clicked.connect(self.choose_background_color)
        self.text_color_button.clicked.connect(self.choose_text_color)
        self.add_file_button.clicked.connect(self.add_file)
        self.load_file_button.clicked.connect(self.load_file)
        self.open_all_books_button.clicked.connect(self.open_all_books)
        self.link_open_button.clicked.connect(self.open_link)

        self.tableWidget.itemDoubleClicked.connect(self.load_text)

        self.font_size_box.valueChanged.connect(self.font_size)
        self.font_style_box.currentTextChanged.connect(self.font_style)

        self.name_textEdit.textChanged.connect(self.find_files)
        self.author_textEdit.textChanged.connect(self.find_files)
        self.genre_comboBox.activated[str].connect(self.find_files)
        # всякие настроечные моменты
        self.fname = ''
        self.link = None

        self.modified = {}
        self.titles = []

        self.con.create_collation("BINARY", sqlite_nocase_collation)
        self.con.create_collation("NOCASE", sqlite_nocase_collation)

        self.con.create_function("LIKE", 2, sqlite_like)

    def eventFilter(self, obj, event):  # отображает диалоговое окно с инфой о разработчике
        if event.type() == QEvent.MouseButtonPress:
            self.dialog = QDialog(self)
            self.dialog.resize(300, 300)
            self.dialog.setWindowTitle('Информация о проекте')
            self.btn = QPushButton(self.dialog)
            self.btn.move(80, 50)
            self.btn.setText('Информация о проекте')
            self.btn.clicked.connect(self.info)
            self.label_11 = QLabel(self.dialog)
            self.label_11.move(80, 100)
            self.label_11.setText('Проект создан ***.\n\nХорошего дня :)')
            self.label_12 = QLabel(self.dialog)
            self.label_12.resize(64, 64)
            self.pixmap = QPixmap('texts/smile.jpg')
            self.label_12.setPixmap(self.pixmap)
            self.label_12.move(118, 200)

            self.dialog.show()
        return super(QMainWindow, self).eventFilter(obj, event)

    def info(self):  # открытие файла с "помощью" во вкладке чтения книг
        self.dialog.close()
        f = open('texts/info.txt', mode='r', encoding='utf-8')
        g = f.read()
        self.textBrowser.setText(g)
        self.tabWidget.setCurrentIndex(1)

    def open_all_books(self):  # отображение всех имеющихся в базу книг в таблице во вкладке "Поиск"
        cur = self.con.cursor()
        if self.genre_comboBox.currentText() != 'Любой':
            request = """ and G.id in (SELECT id from Genre where G.genre = '""" + \
                      self.genre_comboBox.currentText() + """')"""
        else:
            request = """"""
        result = cur.execute(
            """select B.id, B.name, A.author, G.genre, B.year 
            from Books B, Author A, Genre G 
            where B.author_id = A.id 
            and B.genre_id = G.id""" + request).fetchall()

        self.tableWidget.setRowCount(len(result))
        if len(result) > 0:
            self.tableWidget.setColumnCount(len(result[0]))
            self.titles = [description[0] for description in cur.description]
            for i, elem in enumerate(result):
                for j, val in enumerate(elem):
                    self.tableWidget.setItem(i, j, QTableWidgetItem(str(val)))

        self.tableWidget.hideColumn(0)
        self.tableWidget.setColumnWidth(4, self.tableWidget.width() * 0.08)
        self.tableWidget.setColumnWidth(1, self.tableWidget.width() * 0.35)
        self.tableWidget.setColumnWidth(2, self.tableWidget.width() * 0.35)
        self.tableWidget.setColumnWidth(3, self.tableWidget.width() * 0.2)

        self.tableWidget.setHorizontalHeaderLabels(['', 'Название книги', 'Автор', 'Жанр', 'Год'])

    def find_files(self):
        # поиск книг в базе по введенным автору / названию с учетом выбранного жанра (поиск динамический)
        cur = self.con.cursor()
        if self.author_textEdit.text() == '' and self.name_textEdit.text() == '':
            request = """and UPPER(A.author) like '%a%'"""

        elif self.author_textEdit.text() == '':
            request = """and UPPER(B.name) like '%""" + self.name_textEdit.text().upper() + """%'"""

        elif self.name_textEdit.text() == '':
            request = """and UPPER(A.author) like '%""" + self.author_textEdit.text().upper() + """%'"""

        else:
            request = """and UPPER(A.author) like '%""" + self.author_textEdit.text().upper() + """%'
                    and UPPER(B.name) like '%""" + self.name_textEdit.text().upper() + """%'"""
        if self.genre_comboBox.currentText() != 'Любой':
            request = request + """ and G.id in (SELECT id from Genre where G.genre = '""" + \
                      self.genre_comboBox.currentText() + """')"""
        result = cur.execute(
            """select B.id, B.name, A.author, G.genre, B.year 
            from Books B, Author A, Genre G 
            where B.author_id = A.id 
            and B.genre_id = G.id """ + request).fetchall()

        self.tableWidget.setRowCount(len(result))
        if len(result) > 0:
            self.tableWidget.setColumnCount(len(result[0]))
            self.titles = [description[0] for description in cur.description]
            for i, elem in enumerate(result):
                for j, val in enumerate(elem):
                    self.tableWidget.setItem(i, j, QTableWidgetItem(str(val)))

        self.tableWidget.hideColumn(0)
        self.tableWidget.setColumnWidth(4, self.tableWidget.width() * 0.08)
        self.tableWidget.setColumnWidth(1, self.tableWidget.width() * 0.35)
        self.tableWidget.setColumnWidth(2, self.tableWidget.width() * 0.35)
        self.tableWidget.setColumnWidth(3, self.tableWidget.width() * 0.2)

        self.tableWidget.setHorizontalHeaderLabels(['', 'Название книги', 'Автор', 'Жанр', 'Год'])

    def resizeEvent(self, *args, **kwargs):
        # изменение размеров виджетов при изменении размеров экрана (для красивого отображения)
        self.tableWidget.setColumnWidth(4, self.tableWidget.width() * 0.08)
        self.tableWidget.setColumnWidth(1, self.tableWidget.width() * 0.35)
        self.tableWidget.setColumnWidth(2, self.tableWidget.width() * 0.35)
        self.tableWidget.setColumnWidth(3, self.tableWidget.width() * 0.2)

    def load_text(self):  # отображение текста книги
        if self.tableWidget.selectedItems() == []:
            self.message_label.setText('Выберите книгу')
        else:
            cur = self.con.cursor()

            self.message_label.setText('')
            self.textBrowser.setFontPointSize(self.font_size_box.value())
            self.textBrowser.setFontFamily(self.font_style_box.currentText())

            rows = list(set([i.row() for i in self.tableWidget.selectedItems()]))
            ids = [self.tableWidget.item(i, 0).text() for i in rows]

            self.link = (cur.execute(f"""SELECT link from Books
            where id = {ids[0]}""").fetchone()[0])

            self.tabWidget.setCurrentIndex(1)

            f = open('texts/' + str(ids[0]) + '.txt', mode='r', encoding='utf-8')
            g = f.read()
            self.textBrowser.setText(g)

    def open_link(self):  # открытие ссылки на книгу
        if self.link is not None:
            webbrowser.open_new_tab(self.link)

    def delete_files(self):  # удаление книги
        cur = self.con.cursor()
        if self.tableWidget.selectedItems() == []:
            self.message_label.setText('Выберите книгу')
        else:
            self.message_label.setText('')
            rows = list(set([i.row() for i in self.tableWidget.selectedItems()]))
            ids = [self.tableWidget.item(i, 1).text() for i in rows]
            valid = QMessageBox.question(self, '',
                                         "Действительно удалить элементы с названиями " +
                                         ",".join(ids), QMessageBox.Yes, QMessageBox.No)
            if valid == QMessageBox.Yes:
                cur.execute("""DELETE from Books 
                WHERE name in ('""" +
                            "', '".join(ids) + """')""")
                self.find_files()
                self.con.commit()

    def load_file(self):  # добавление пользовательских книг (с проверкой на валидность введенных данных)
        self.fname = QFileDialog.getOpenFileName(self, 'Выбрать картинку',
                                                 '', "Текст(*.txt)")[0]
        if self.fname != '':
            self.choose_file_label.setText('Выбран файл:' + self.fname)

    def add_file(self):
        cur = self.con.cursor()

        if self.book_name_Edit.text() == '':
            self.status_bar_label.setText('Введите название книги.')
            return

        if self.author_Edit.text() == '':
            self.status_bar_label.setText('Введите автора книги.')
            return

        if self.fname == '':
            self.status_bar_label.setText('Выберите файл с текстом книги.')
            return

        if not self.year_Edit.text().isdigit() and self.year_Edit.text() != '':
            self.status_bar_label.setText('Год должен быть числом.')
            return

        self.status_bar_label.setText('')

        ids = int(cur.execute('SElECT id from Books').fetchall()[-1][0]) + 1
        authors = cur.execute('SELECT author from Author').fetchall()
        authors = [el[0] for el in authors]

        if self.author_Edit.text() in authors:
            author_id = int(cur.execute(
                """SELECT id from Author 
                where author = '""" + self.author_Edit.text() + """'""").fetchall()[-1][0])

        else:
            author_id = cur.execute('SELECT id from Author').fetchall()
            author_id = [int(el[0]) for el in author_id]
            author_id = max(author_id) + 1
            cur.execute("INSERT INTO Author(id, author) VALUES (?, ?)",
                        (author_id, self.author_Edit.text()))

        if self.genre_Edit.text() != '':
            genres = cur.execute('SELECT genre from Genre').fetchall()
            genres = [el[0] for el in genres]
            if self.genre_Edit.text() in genres:
                genre_id = int(
                    cur.execute(
                        """SELECT id from Genre 
                        where genre = '""" + str(self.genre_Edit.text()) + """'""").fetchall()[
                        -1][0])
            else:
                genre_id = cur.execute('SELECT id from Genre').fetchall()
                genre_id = [int(el[0]) for el in genre_id]
                genre_id = max(genre_id) + 1
                cur.execute("INSERT INTO Genre(id, genre) VALUES (?, ?)",
                            (genre_id, self.genre_Edit.text()))
                self.genre_comboBox.addItem(self.genre_Edit.text())
        else:
            genre_id = None
        cur.execute('INSERT INTO Books VALUES (?, ?, ?, ?, ?, ?)',
                    (ids, self.book_name_Edit.text(), author_id,
                     genre_id, self.year_Edit.text(), self.link_Edit.text()))

        self.con.commit()

        self.status_bar_label.setText('Книга добавлена')

        f = open(self.fname, mode='r', encoding='utf-8')
        g = open('texts/' + str(ids) + '.txt', mode='w', encoding='utf-8')
        g.write(f.read())
        f.close()
        g.close()

    def choose_background_color(self):  # выбор цветы фона во вкладке чтения
        color = QColorDialog.getColor()

        if color.isValid():
            self.textBrowser.setStyleSheet("background-color: {}".format(
                color.name()))

    def choose_text_color(self):  # изменение цвета текста
        color = QColorDialog.getColor()

        if color.isValid():
            self.textBrowser.setTextColor(color)
            text = self.textBrowser.toPlainText()
            self.textBrowser.setText(text)

    def font_style(self):  # изменение стиля шрифта
        text = self.textBrowser.toPlainText()
        self.textBrowser.setFontFamily(self.font_style_box.currentText())
        self.textBrowser.setText(text)

    def font_size(self):  # изменение размера шрифта
        text = self.textBrowser.toPlainText()
        self.textBrowser.setFontPointSize(self.font_size_box.value())
        self.textBrowser.setText(text)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyWidget()
    ex.show()
    sys.exit(app.exec_())
