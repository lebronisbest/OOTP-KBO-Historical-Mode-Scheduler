from datetime import datetime, timedelta, date
import itertools
import calendar
import random
import hashlib

### 입력 및 올스타 날짜 관련 함수
def get_user_input():
    num_teams = int(input("팀 수를 입력하세요 (예: 10): "))
    opening_date_str = input("개막일을 입력하세요 (YYYY-MM-DD 형식): ")
    games_between_teams = int(input("각 팀 간 총 경기 수 (예: 16): "))
    allstar_week_n = int(input("올스타 주간은 7월 몇 번째 주인가요? (예: 2): "))
    opening_date = datetime.strptime(opening_date_str, "%Y-%m-%d").date()
    return num_teams, opening_date, games_between_teams, allstar_week_n

def get_ootp_header_input():
    schedule_type = input("OOTP 스케줄 type을 입력하세요 (예: CUSTOM): ").strip()
    inter_league = input("인터리그 여부? (1=사용, 0=비사용): ").strip()
    balanced_games = input("균형 일정 여부? (1=사용, 0=비사용): ").strip()
    return schedule_type, inter_league, balanced_games

def get_allstar_dates(year, week_num):
    # 7월의 모든 금요일을 찾고, 그 다음 토/일이 모두 7월인 경우 선택
    july_dates = []
    for day in range(1, 32):
        try:
            d = date(year, 7, day)
            july_dates.append(d)
        except ValueError:
            break
    
    valid_triples = []
    for fri in july_dates:
        if fri.weekday() != 4:  # 금요일이 아닌 경우 건너뜀
            continue
        sat = fri + timedelta(days=1)
        sun = fri + timedelta(days=2)
        if sat.month == 7 and sun.month == 7:
            valid_triples.append( (fri, sat, sun) )
    
    if week_num > len(valid_triples):
        raise ValueError(f"7월에는 {len(valid_triples)}개의 올스타 주간이 있습니다. {week_num}번째 주간은 존재하지 않습니다.")
    
    return valid_triples[week_num - 1]



### 시리즈 생성: 주어진 경기수를 2연전, 3연전 등으로 분할
def generate_series(total_games):
    result = []
    while total_games > 0:
        if total_games == 2:
            result.append(2)
            total_games -= 2
        elif total_games == 4:
            result.extend([2, 2])
            total_games -= 4
        else:
            result.append(3)
            total_games -= 3
    return result

### 올스타 및 월요일 등 휴식일을 제외한 사용 가능한 날짜 리스트 생성
def get_available_dates(opening_date, allstar_fri, allstar_sat, allstar_sun, count=500):
    excluded = {allstar_fri, allstar_sat, allstar_sun}
    dates = []
    i = 0
    while len(dates) < count:
        d = opening_date + timedelta(days=i)
        if d.weekday() != 0 and d not in excluded:
            dates.append(d)
        i += 1
    return dates


### 시리즈 시작 요일 조건: 2연전은 수/토, 3연전은 화/금
def is_valid_series_start(series_length, start_date):
    weekday = start_date.weekday()
    if series_length == 2:
        return weekday in (1, 3, 5)  # 화, 목, 토
    elif series_length == 3:
        return weekday in (1, 4)     # 화, 금 (그대로 유지)
    return False

def generate_schedule(num_teams, opening_date, games_between_teams, allstar_week_n, available_dates):
    year = opening_date.year
    allstar_fri, allstar_sat, allstar_sun = get_allstar_dates(year, allstar_week_n)
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

    random.shuffle(all_series)

    # 개막전 2연전 배정
    opening_2games = []
    used_teams = set()
    for s in all_series:
        if s['length'] == 2 and s['home'] not in used_teams and s['away'] not in used_teams:
            opening_2games.append(s)
            used_teams.update([s['home'], s['away']])
    for s in opening_2games:
        all_series.remove(s)

    schedule = {}
    team_busy = {t: set() for t in teams}

    # 개막전 배정
    for s in opening_2games:
        for offset in range(s['length']):
            date_ = available_dates[offset]
            schedule.setdefault(date_, []).append((s['home'], s['away']))
            team_busy[s['home']].add(date_)
            team_busy[s['away']].add(date_)

    start_idx = 2  # 개막전 이후부터 시작

    # 시리즈 분리
    three_game_series = [s for s in all_series if s['length'] == 3]
    two_game_series = [s for s in all_series if s['length'] == 2]

    # ⚾ 1단계: 3연전 먼저 배정
    for idx in range(start_idx, len(available_dates)):
        real_date = available_dates[idx]
        placed_today = []
        used_teams = set()

        for s in three_game_series[:]:
            if not is_valid_series_start(s['length'], real_date):
                continue

            days_needed = [idx + i for i in range(s['length'])]
            if any(d >= len(available_dates) for d in days_needed):
                continue

            dates_needed = [available_dates[d] for d in days_needed]
            if any((dates_needed[i+1] - dates_needed[i]).days != 1 for i in range(len(dates_needed) - 1)):
                continue

            if any(date in team_busy[s['home']] or date in team_busy[s['away']] for date in dates_needed):
                continue

            if s['home'] in used_teams or s['away'] in used_teams:
                continue

            for d_ in dates_needed:
                schedule.setdefault(d_, []).append((s['home'], s['away']))
                team_busy[s['home']].add(d_)
                team_busy[s['away']].add(d_)

            used_teams.update([s['home'], s['away']])
            placed_today.append(s)

        for s in placed_today:
            three_game_series.remove(s)

        if not three_game_series:
            break  # 3연전 다 배정됐으면 중단

    # ⚾ 2단계: 2연전 배정
    for idx in range(start_idx, len(available_dates)):
        real_date = available_dates[idx]
        placed_today = []
        used_teams = set()

        for s in two_game_series[:]:
            if not is_valid_series_start(s['length'], real_date):
                continue

            days_needed = [idx + i for i in range(s['length'])]
            if any(d >= len(available_dates) for d in days_needed):
                continue

            dates_needed = [available_dates[d] for d in days_needed]
            if any((dates_needed[i+1] - dates_needed[i]).days != 1 for i in range(len(dates_needed) - 1)):
                continue

            if any(date in team_busy[s['home']] or date in team_busy[s['away']] for date in dates_needed):
                continue

            if s['home'] in used_teams or s['away'] in used_teams:
                continue

            for d_ in dates_needed:
                schedule.setdefault(d_, []).append((s['home'], s['away']))
                team_busy[s['home']].add(d_)
                team_busy[s['away']].add(d_)

            used_teams.update([s['home'], s['away']])
            placed_today.append(s)

        for s in placed_today:
            two_game_series.remove(s)

        if not two_game_series:
            break  # 2연전도 모두 배정되면 종료

    # 올스타전 배정
    schedule.setdefault(allstar_sat, []).append(('올스타', '올스타'))
    return schedule


### 후처리: 전체 일정 기간을 최소 170일로 "스트레칭" (골고루 분포)
from datetime import timedelta

from datetime import timedelta

def stretch_schedule(schedule, opening_date, min_span=170, allstar_week_n=None):
    allstar_fri, allstar_sat, allstar_sun = get_allstar_dates(opening_date.year, allstar_week_n)

    print("\n🟡 올스타 주간:")
    print("  금요일:", allstar_fri)
    print("  토요일:", allstar_sat)
    print("  일요일:", allstar_sun)

    # 개막일부터 7일은 고정 (개막 주간)
    fixed_opening_dates = set(opening_date + timedelta(days=i) for i in range(7))
    excluded_dates = {allstar_fri, allstar_sat, allstar_sun} | fixed_opening_dates
    used_dates = set(excluded_dates)

    # 시리즈 단위로 묶기
    date_to_games = {d: schedule[d] for d in schedule if d not in excluded_dates}
    dates_sorted = sorted(date_to_games.keys())

    series_list = []
    buffer = []
    prev_date = None
    prev_game_set = None

    for d in dates_sorted:
        games = date_to_games[d]
        game_set = frozenset(games)
        if not buffer:
            buffer.append((d, games))
            prev_date = d
            prev_game_set = game_set
        elif (d - prev_date).days == 1 and game_set == prev_game_set:
            buffer.append((d, games))
            prev_date = d
        else:
            series_list.append(buffer)
            buffer = [(d, games)]
            prev_date = d
            prev_game_set = game_set
    if buffer:
        series_list.append(buffer)

    # 기존 기간 계산
    if not series_list:
        return schedule

    first_day = min(d for d in date_to_games)
    last_day = max(d for d in date_to_games)
    current_span = (last_day - first_day).days + 1

    print(f"\n📏 기존 스케줄 기간: {current_span}일")

    if current_span >= min_span:
        print("✅ stretch 불필요. 기존 스케줄 유지.")
        return schedule

    factor = min_span / current_span
    new_schedule = {}

    for series in series_list:
        base_day = series[0][0]
        offset = (base_day - opening_date).days
        new_offset = round(offset * factor)
        new_start = opening_date + timedelta(days=new_offset)

        # 시리즈 연속 날짜 확보 (월요일 포함 안 됨)
        new_dates = []
        i = 0
        while True:
            candidate_dates = []
            j = 0
            while len(candidate_dates) < len(series):
                cand = new_start + timedelta(days=i + j)
                if cand.weekday() != 0 and cand not in used_dates:
                    candidate_dates.append(cand)
                else:
                    break  # 월요일이 포함되면 전체 시리즈 후보 폐기
                j += 1

            if len(candidate_dates) == len(series):
                new_dates = candidate_dates
                break  # 연속 가능한 날짜 확보

            i += 1  # 다음 시작 날짜 시도

        for (_, games), new_day in zip(series, new_dates):
            new_schedule.setdefault(new_day, []).extend(games)
            used_dates.add(new_day)

    # 고정된 날짜 복원
    new_schedule[allstar_fri] = []  # 금요일은 경기 없음
    new_schedule[allstar_sun] = []  # 일요일도 없음
    new_schedule[allstar_sat] = [('올스타', '올스타')]  # 토요일은 올스타전

    for d in fixed_opening_dates:
        if d in schedule:
            new_schedule[d] = schedule[d]

    return new_schedule

### HTML 시각화: 간단한 vs 2 @ 1 포맷, 색상 추가
import hashlib
import calendar
from datetime import date


def save_schedule_to_html(schedule, opening_date, num_teams):
    import os
    import hashlib
    import calendar
    from datetime import date

    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    file_path = os.path.join(desktop, "calendar_schedule.html")

    html = """<html><head><meta charset="UTF-8"><title>경기 일정 달력</title>
    <style>
    body { font-family: Arial; }
    table { border-collapse: collapse; margin-bottom: 30px; }
    th, td { border: 1px solid #999; padding: 5px; vertical-align: top; width: 14.2%; }
    .game { margin: 2px 0; padding: 2px; border-radius: 4px; color: white; font-size: 12px; }
    .allstar { background-color: gold !important; color: black !important; font-weight: bold; }
    select { margin: 10px 0; padding: 5px; }
    .hidden { display: none; }
    </style>
    <script>
    function filterTeam() {
        const selected = document.getElementById("teamSelect").value;
        const allGames = document.querySelectorAll(".game");
        let home = 0, away = 0;

        allGames.forEach(g => {
            const h = g.getAttribute("data-home");
            const a = g.getAttribute("data-away");

            if (selected === "all") {
                g.classList.remove("hidden");
                g.innerText = `${parseInt(h)+1} VS ${parseInt(a)+1}`;
            } else {
                if (h === selected) {
                    g.classList.remove("hidden");
                    g.innerText = `VS${parseInt(a)+1}`;
                    home += 1;
                } else if (a === selected) {
                    g.classList.remove("hidden");
                    g.innerText = `@${parseInt(h)+1}`;
                    away += 1;
                } else {
                    g.classList.add("hidden");
                }
            }
        });

        const stat = document.getElementById("statLine");
        if (selected === "all") {
            stat.innerText = "";
        } else {
            const total = home + away;
            stat.innerText = `총 ${total}경기 (홈 ${home}, 원정 ${away})`;
        }
    }
    </script></head><body>
    <h1>경기 일정 달력</h1>
    <label for="teamSelect">팀 선택:</label>
    <select id="teamSelect" onchange="filterTeam()">
      <option value="all">전체 보기</option>"""

    for t in range(num_teams):
        html += f'<option value="{t}">팀 {t+1}</option>'
    html += "</select>\n<div id='statLine' style='margin: 10px 0; font-weight: bold;'></div>"

    def color_for_series(home, away):
        uid = f"{min(home, away)}_{max(home, away)}"
        hex_code = hashlib.md5(uid.encode()).hexdigest()[:6]
        return f"#{hex_code}"

    cal = calendar.HTMLCalendar(calendar.SUNDAY)
    months = sorted(set((d.year, d.month) for d in schedule))
    for year, month in months:
        html += f"<h2>{year}년 {month}월</h2><table><tr>"
        headers = ['일', '월', '화', '수', '목', '금', '토']
        html += ''.join(f"<th>{h}</th>" for h in headers) + "</tr>"
        month_days = cal.monthdayscalendar(year, month)
        for week in month_days:
            html += "<tr>"
            for day in week:
                if day == 0:
                    html += "<td></td>"
                    continue
                this_date = date(year, month, day)
                html += f"<td><strong>{day}</strong><br>"
                for g in schedule.get(this_date, []):
                    if g == ('올스타', '올스타'):
                        html += '<div class="game allstar" data-home="all" data-away="all">🌟 올스타전</div>'
                    else:
                        h, a = g
                        color = color_for_series(h, a)
                        html += f'<div class="game" data-home="{h}" data-away="{a}" style="background-color:{color}">{h+1} VS {a+1}</div>'
                html += "</td>"
            html += "</tr>"
        html += "</table>"

    html += "</body></html>"

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n📅 최종 달력 저장 완료: {file_path}")

def export_schedule_to_ootp_xml(
    schedule,
    opening_date,
    num_teams,
    allstar_sat,
    schedule_type="CUSTOM",
    inter_league="1",
    balanced_games="0",
    filename="ootp_schedule.lsdl"
):
    import random
    from xml.etree.ElementTree import Element, SubElement, tostring
    import xml.dom.minidom
    import holidays

    # ✅ OOTP 요일 변환: 월=0 → 2, ..., 토=5 → 7, 일=6 → 1
    start_dow = (opening_date.weekday() + 2) % 7 or 7

    # ✅ allstar_game_day 계산
    allstar_day_num = (allstar_sat - opening_date).days + 1

    # ✅ 팀당 경기 수 계산
    total_games = sum(
        len(games) for d, games in schedule.items()
        if games and games[0] != ('올스타', '올스타')
    )
    games_per_team = total_games * 2 // num_teams

    # ✅ 공휴일 목록 생성 (대한민국)
    kr_holidays = holidays.KR(years=opening_date.year)

    # ✅ XML 루트 생성
    root = Element("SCHEDULE", {
        "type": schedule_type,
        "inter_league": inter_league,
        "balanced_games": balanced_games,
        "games_per_team": str(games_per_team),
        "start_month": str(opening_date.month),
        "start_day": str(opening_date.day),
        "start_day_of_week": str(start_dow),
        "allstar_game_day": str(allstar_day_num)
    })

    games_tag = SubElement(root, "GAMES")

    all_dates = sorted(schedule.keys())
    date_to_daynum = {d: (d - opening_date).days + 1 for d in all_dates}

    for game_date in all_dates:
        daynum = date_to_daynum[game_date]
        for game in schedule[game_date]:
            if game == ('올스타', '올스타'):
                continue

            home, away = game
            weekday = game_date.weekday()
            month = game_date.month

            # ✅ 시간 배정 로직
            if game_date in kr_holidays:
                time = "1700"
            elif weekday in (5, 6):  # 토/일
                time = "1700"
            else:
                time = "1830"

            # ✅ 봄/가을 1700인 날 → 50% 확률로 1400
            if time == "1700" and not (6 <= month <= 8) and game_date not in kr_holidays:
                time = random.choice(["1400", "1700"])

            SubElement(games_tag, "GAME", {
                "day": str(daynum),
                "time": time,
                "home": str(home + 1),
                "away": str(away + 1)
            })

    # ✅ XML 저장
    raw_xml = tostring(root, encoding="utf-8")
    pretty_xml = xml.dom.minidom.parseString(raw_xml).toprettyxml(indent="  ")

    with open(filename, "w", encoding="utf-8") as f:
        f.write(pretty_xml)

    print(f"\n📤 OOTP XML 스케줄 저장 완료: {filename}")

def main():
    # 사용자 입력 받기
    num_teams, opening_date, games_between_teams, allstar_week_n = get_user_input()

    # 올스타 날짜 계산
    allstar_fri, allstar_sat, allstar_sun = get_allstar_dates(opening_date.year, allstar_week_n)

    # 팀 조합 및 시리즈 생성
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

    # 사용 가능한 날짜 계산
    total_game_days = sum(s['length'] for s in all_series)
    date_buffer = 20
    available_dates = get_available_dates(
        opening_date, allstar_fri, allstar_sat, allstar_sun, total_game_days + date_buffer
    )

    # 스케줄 생성
    schedule = generate_schedule(
        num_teams,
        opening_date,
        games_between_teams,
        allstar_week_n,
        available_dates
    )

    # stretch 적용 여부
    use_stretch = input("경기 일정을 최소 170일로 늘리는 stretch 기능을 사용할까요? (Y/N): ").strip().lower() == 'y'
    if use_stretch:
        print("\n🔧 stretch 기능 적용 중...")
        schedule = stretch_schedule(schedule, opening_date, 170, allstar_week_n)
    else:
        print("\n✅ stretch 미적용, 가능한 한 촘촘히 배정합니다.")
        rest_days = [d for d in sorted(schedule)
                     if d.weekday() != 0 and d not in {allstar_fri, allstar_sat, allstar_sun}
                     and not schedule[d]]
        if rest_days:
            print(f"⚠️ 경기 없는 날이 {len(rest_days)}일 있습니다: 예시 → {[d.strftime('%Y-%m-%d') for d in rest_days[:3]]}")
        else:
            print("🎉 경기 없는 날 없이 촘촘하게 구성됐습니다.")

    # 일정 콘솔 출력
    print("\n✅ 최종 생성된 일정:")
    for d in sorted(schedule):
        print(f"\n{d.strftime('%Y-%m-%d')} ({'월화수목금토일'[d.weekday()]}):")
        for g in schedule[d]:
            if g == ('올스타', '올스타'):
                print("  🌟 올스타전")
            else:
                h, a = g
                print(f"  vs 팀 {a+1} @ 팀 {h+1}")

    # HTML 시각화 저장
    save_schedule_to_html(schedule, opening_date, num_teams)

    # OOTP XML 속성 입력
    schedule_type, inter_league, balanced_games = get_ootp_header_input()

    # OOTP XML 저장
    export_schedule_to_ootp_xml(
        schedule,
        opening_date,
        num_teams,
        allstar_sat,
        schedule_type=schedule_type,
        inter_league=inter_league,
        balanced_games=balanced_games,
        filename="ootp_schedule.lsdl"
    )

def generate_type_attribute(games_per_team, structure, num_teams):
    if len(structure) == 1:
        prefix = "ILN"
    elif len(structure) == 2:
        prefix = "ILY"
    else:
        prefix = "ILY"  # fallback

    parts = []
    for i, divisions in enumerate(structure, start=1):
        inner = ''.join(f"D{j+1}T{team_count}" for j, team_count in enumerate(divisions))
        parts.append(f"SL{i}{inner}")

    return f"{prefix}_BGN_G{games_per_team * (num_teams - 1)}_" + ''.join(parts)



if __name__ == '__main__':
    main()
