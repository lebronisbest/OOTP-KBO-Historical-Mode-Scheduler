import sys
import os
import itertools
from functools import partial
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QSpinBox, QVBoxLayout, QCalendarWidget,
    QComboBox, QFileDialog, QMessageBox, QCheckBox, QGridLayout, QGroupBox, QScrollArea
)
from PyQt5.QtCore import QDate, Qt
from PyQt5.QtGui import QPixmap

from baseball_scheduler import (
    get_allstar_dates,
    get_available_dates,
    generate_schedule,
    stretch_schedule,
    save_schedule_to_html,
    export_schedule_to_ootp_xml,
    generate_type_attribute,
    generate_series,
)


class SchedulerGUI(QWidget):
    def resource_path(self, relative_path):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.abspath("."), relative_path)

    def __init__(self):
        super().__init__()
        self.structure_presets = []
        self.structure_widgets = []

        self.setWindowTitle("OOTP KBO 히스토리컬 모드 스케줄 생성기")
        self.setGeometry(100, 100, 640, 720)
        self.setStyleSheet("""
            QWidget {
                background-color: #2b3e50;
                color: #ecf0f1;
                font-family: 'Segoe UI';
                font-size: 11pt;
            }
            QLabel {
                color: #ecf0f1;
            }
            QGroupBox {
                border: 1px solid #34495e;
                margin-top: 10px;
                padding: 8px;
                font-weight: bold;
                color: #1abc9c;
            }
            QSpinBox, QComboBox, QPushButton {
                background-color: #34495e;
                color: #ecf0f1;
                border-radius: 4px;
                padding: 4px 6px;
            }
            QPushButton:hover {
                background-color: #3c6382;
            }
        """)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        main_layout = QVBoxLayout(container)

        logo_path = self.resource_path("대지 1.png")
        if os.path.exists(logo_path):
            logo_label = QLabel()
            logo_pixmap = QPixmap(logo_path)
            logo_pixmap = logo_pixmap.scaledToHeight(300, Qt.SmoothTransformation)
            logo_label.setPixmap(logo_pixmap)
            logo_label.setAlignment(Qt.AlignCenter)
            main_layout.addWidget(logo_label)

        self.presets = {
            "1982-1985 KBO 히스토리컴 (2리그, 동군 3팀, 서군 3팀)": [[3], [3]],
            "1986-1990 KBO 히스토리컴 (2리그, 동군 3팀, 서군 4팀)": [[3], [4]],
            "1991-2012 KBO 히스토리컴 (2리그, 동군 4팀, 서군 4팀)": [[4], [4]],
            "2013-2014 KBO 히스토리컴 (2리그, 동군 4팀, 서군 5팀)": [[4], [5]],
            "2015~ KBO 히스토리컴 (2리그, 동군 5팀, 서군 5팀)": [[5], [5]],
        }

        self.preset_combo = QComboBox()
        self.preset_combo.addItem("직접 설정")
        for name in self.presets.keys():
            self.preset_combo.addItem(name)
        self.preset_combo.currentIndexChanged.connect(self.apply_preset)
        main_layout.addWidget(QLabel("리그 구조 프리셋"))
        main_layout.addWidget(self.preset_combo)

        self.structure_group = QGroupBox("리그 구조 설정")
        structure_layout = QVBoxLayout()
        self.subleague_spin = QSpinBox()
        self.subleague_spin.setMinimum(1)
        self.subleague_spin.setMaximum(2)
        self.subleague_spin.valueChanged.connect(self.build_structure_inputs)
        structure_layout.addWidget(QLabel("서브 리그 수"))
        structure_layout.addWidget(self.subleague_spin)
        self.structure_grid = QGridLayout()
        structure_layout.addLayout(self.structure_grid)
        self.structure_group.setLayout(structure_layout)
        main_layout.addWidget(self.structure_group)

        self.team_count_label = QLabel("청 팀 수: 0")
        main_layout.addWidget(self.team_count_label)

        self.games_input = QSpinBox()
        self.games_input.setMinimum(1)
        self.games_input.setMaximum(100)
        self.games_input.setValue(16)

        self.allstar_week_input = QSpinBox()
        self.allstar_week_input.setMinimum(1)
        self.allstar_week_input.setMaximum(5)
        self.allstar_week_input.setValue(2)

        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.clicked.connect(self.check_saturday)
        self.calendar.setStyleSheet("""
            QCalendarWidget QWidget {
                alternate-background-color: #2b3e50;
                color: #ecf0f1;
                background-color: #2b3e50;
                }

            QCalendarWidget QAbstractItemView:enabled {
                background-color: #34495e;
                color: #ecf0f1;
                selection-background-color: #2980b9;  /* 선택된 날짜 색상 */
                selection-color: #ffffff;
                gridline-color: #7f8c8d;
                }

            QCalendarWidget QToolButton {
                background-color: #3c6382;  /* 월/년 변경 버튼 배경 */
                color: #ecf0f1;
                border: none;
                font-weight: bold;
                }

            QCalendarWidget QSpinBox {
            background-color: #34495e;
            color: #ecf0f1;
            border: none;
                }
        """)


        self.stretch_check = QCheckBox("170일 stretch 사용(시즌 총 길이가 170일 미만 일 시 휴식일을 삽입하여 170일 이상으로 만듭니다.)")
        self.inter_league_check = QCheckBox("인터리그")
        self.balanced_check = QCheckBox("균형 잡힌 스케줄")

        main_layout.addWidget(QLabel("팀 간 게임 수"))
        main_layout.addWidget(self.games_input)
        main_layout.addWidget(QLabel("올스타 주간 (7월 n째 주)"))
        main_layout.addWidget(self.allstar_week_input)
        main_layout.addWidget(QLabel("개막일 선택"))
        main_layout.addWidget(self.calendar)
        main_layout.addWidget(self.stretch_check)
        main_layout.addWidget(self.inter_league_check)
        main_layout.addWidget(self.balanced_check)

        self.save_button = QPushButton("스케줄 생성 및 저장")
        self.save_button.clicked.connect(self.generate_and_save)  # 연결 유지
        main_layout.addWidget(self.save_button)

        scroll.setWidget(container)
        layout = QVBoxLayout(self)
        layout.addWidget(scroll)
        self.setLayout(layout)

        self.build_structure_inputs()


    def apply_preset(self, index):
        if index == 0:
            return  # 직접 설정
        preset_name = self.preset_combo.itemText(index)
        if preset_name in self.presets:
            self.structure_presets = self.presets[preset_name]
            self.subleague_spin.blockSignals(True)
            self.subleague_spin.setValue(len(self.structure_presets))
            self.subleague_spin.blockSignals(False)
            self.build_structure_inputs(from_preset=True)

    def build_structure_inputs(self, from_preset=False):
        # 기존 위젯 제거
        for i in reversed(range(self.structure_grid.count())):
            widget = self.structure_grid.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        self.structure_widgets.clear()
        structure = self.structure_presets if from_preset else []

        for sl_index in range(self.subleague_spin.value()):
            self.structure_grid.addWidget(QLabel(f"서브 리그 {sl_index+1}"), sl_index * 10, 0, 1, 2)

            division_spin = QSpinBox()
            division_spin.setMinimum(1)
            division_spin.setMaximum(3)
            division_count = structure[sl_index] if from_preset and sl_index < len(structure) else [5, 5]
            division_spin.setValue(len(division_count))
            division_spin.valueChanged.connect(partial(self.update_division_rows, sl_index))
            self.structure_grid.addWidget(QLabel("디비전 수:"), sl_index * 10 + 1, 0)
            self.structure_grid.addWidget(division_spin, sl_index * 10 + 1, 1)

            team_spins = []
            for i in range(division_spin.value()):
                label = QLabel(f"디비전 내 팀 {i+1}:")
                spin = QSpinBox()
                spin.setMinimum(1)
                spin.setMaximum(20)
                spin.setValue(division_count[i] if i < len(division_count) else 5)
                spin.valueChanged.connect(self.update_team_count)
                self.structure_grid.addWidget(label, sl_index * 10 + 2 + i, 0)
                self.structure_grid.addWidget(spin, sl_index * 10 + 2 + i, 1)
                team_spins.append(spin)

            self.structure_widgets.append((division_spin, team_spins))

        self.update_team_count()

    def update_division_rows(self, sl_index):
        division_spin, team_spins = self.structure_widgets[sl_index]

        for spin in team_spins:
            spin.setParent(None)
        team_spins.clear()

        for i in range(division_spin.value()):
            label = QLabel(f"디비전 내 팀 {i+1}:")
            spin = QSpinBox()
            spin.setMinimum(1)
            spin.setMaximum(20)
            spin.setValue(5)
            spin.valueChanged.connect(self.update_team_count)
            self.structure_grid.addWidget(label, sl_index * 10 + 2 + i, 0)
            self.structure_grid.addWidget(spin, sl_index * 10 + 2 + i, 1)
            team_spins.append(spin)

        self.update_team_count()

    def update_team_count(self):
        total = 0
        for _, team_spins in self.structure_widgets:
            total += sum(spin.value() for spin in team_spins)
        self.team_count_label.setText(f"총 팀 수: {total}")

    def check_saturday(self):
        selected_date = self.calendar.selectedDate()
        if selected_date.dayOfWeek() != 6:
            QMessageBox.warning(self, "주의", "개막일은 토요일만 가능합니다!")
            while selected_date.dayOfWeek() != 6:
                selected_date = selected_date.addDays(1)
            self.calendar.setSelectedDate(selected_date)

    def parse_structure(self):
        structure = []
        for _, team_spins in self.structure_widgets:
            structure.append([spin.value() for spin in team_spins])
        return structure

    def generate_and_save(self):
        try:
            structure = self.parse_structure()
            num_teams = sum(sum(division) for division in structure)
            games_between_teams = self.games_input.value()
            allstar_week_n = self.allstar_week_input.value()
            qdate = self.calendar.selectedDate()
            opening_date = qdate.toPyDate()

            allstar_fri, allstar_sat, allstar_sun = get_allstar_dates(opening_date.year, allstar_week_n)

            teams = list(range(num_teams))
            pairings = list(itertools.combinations(teams, 2))
            all_series = []
            for home, away in pairings:
                home_games = games_between_teams // 2
                away_games = games_between_teams - home_games
                for l in generate_series(home_games):
                    all_series.append({'home': home, 'away': away, 'length': l})
                for l in generate_series(away_games):
                    all_series.append({'home': away, 'away': home, 'length': l})

            total_game_days = sum(s['length'] for s in all_series)
            available_dates = get_available_dates(opening_date, allstar_fri, allstar_sat, allstar_sun, total_game_days + 20)

            schedule = generate_schedule(num_teams, opening_date, games_between_teams, allstar_week_n, available_dates)

            if self.stretch_check.isChecked():
                schedule = stretch_schedule(schedule, opening_date, 170, allstar_week_n)

            save_schedule_to_html(schedule, opening_date, num_teams)

            QMessageBox.information(self, "달력 저장 완료", "calendar_schedule.html 파일이 생성되었습니다.")

            save_path, _ = QFileDialog.getSaveFileName(self, "OOTP 스케줄 저장", "ootp_schedule.lsdl", "LSDL Files (*.lsdl)")
            if save_path:
                schedule_type = generate_type_attribute(games_between_teams, structure, num_teams)
                export_schedule_to_ootp_xml(
                    schedule,
                    opening_date,
                    num_teams,
                    allstar_sat,
                    schedule_type=schedule_type,
                    inter_league="1" if self.inter_league_check.isChecked() else "0",
                    balanced_games="1" if self.balanced_check.isChecked() else "0",
                    filename=save_path
                )
                QMessageBox.information(self, "완료", f"스케줄이 저장되었습니다:\n{save_path}")
            else:
                QMessageBox.warning(self, "경고", "파일 저장이 취소되었습니다.")
        except Exception as e:
            QMessageBox.critical(self, "오류", str(e))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = SchedulerGUI()
    gui.show()
    sys.exit(app.exec_())
