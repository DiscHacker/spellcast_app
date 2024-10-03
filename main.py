if __name__ == '__main__':
    print('INITIALIZING...')
    from PyQt5.QtWidgets import QApplication
    import sys
    from src.app import App

    app = QApplication(sys.argv)
    ex = App()
    ex.show()
    sys.exit(app.exec_())