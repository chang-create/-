"""
🔥 V3.4 단타 매매 러너 - Enhanced UI with Rich & Colorama
Beautiful UI scalping runner with modern interface + Rich tables + Color system
"""

import asyncio
import time
import ntplib
from datetime import datetime, timedelta
from scalping_engine import *

# ================================================================================
# 🎨 Enhanced UI 라이브러리 임포트
# ================================================================================
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.layout import Layout
    from rich.live import Live
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.align import Align
    from rich.columns import Columns
    from rich.tree import Tree
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("⚠️ Rich 라이브러리가 없습니다. 기본 UI로 실행됩니다.")
    print("💡 설치: pip install rich")

try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False
    print("⚠️ Colorama 라이브러리가 없습니다. 색상 없이 실행됩니다.")
    print("💡 설치: pip install colorama")

# ================================================================================
# 🎨 Enhanced Console 설정
# ================================================================================
if RICH_AVAILABLE:
    console = Console()
else:
    console = None

def print_enhanced(text, style="white", panel=False, title=""):
    """Enhanced 출력 함수"""
    if RICH_AVAILABLE and console:
        if panel:
            console.print(Panel(text, title=title, style=style))
        else:
            console.print(text, style=style)
    elif COLORAMA_AVAILABLE:
        color_map = {
            "red": Fore.RED,
            "green": Fore.GREEN,
            "yellow": Fore.YELLOW,
            "blue": Fore.BLUE,
            "magenta": Fore.MAGENTA,
            "cyan": Fore.CYAN,
            "white": Fore.WHITE,
            "bright_red": Fore.LIGHTRED_EX,
            "bright_green": Fore.LIGHTGREEN_EX,
            "bright_yellow": Fore.LIGHTYELLOW_EX,
            "bright_blue": Fore.LIGHTBLUE_EX,
        }
        color = color_map.get(style, Fore.WHITE)
        print(f"{color}{text}")
    else:
        print(text)

def create_status_table(title, data):
    """Rich 상태 테이블 생성"""
    if not RICH_AVAILABLE:
        # 기본 테이블 출력
        print(f"\n=== {title} ===")
        for key, value in data.items():
            print(f"{key}: {value}")
        return
    
    table = Table(title=title, box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("항목", style="cyan", no_wrap=True)
    table.add_column("상태", style="green")
    
    for key, value in data.items():
        table.add_row(key, str(value))
    
    console.print(table)

def create_progress_bar(description, total=100):
    """Rich 프로그레스 바 생성"""
    if not RICH_AVAILABLE:
        return None
    
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console
    )

# ================================================================================
# 🕐 V2 방식 NTP 타임서버 시간 관리 시스템 (Enhanced UI)
# ================================================================================

# 글로벌 시간 관리 변수 (V2 방식)
_ntp_time_offset = 0
_last_ntp_sync = 0
_ntp_sync_interval = 3600

def sync_ntp_time(force=False):
    """V2 방식: NTP 시간 동기화 (Enhanced UI)"""
    global _ntp_time_offset, _last_ntp_sync
    
    current_time = time.time()
    
    if not force and (current_time - _last_ntp_sync) < _ntp_sync_interval:
        return True
    
    try:
        ntp_servers = [
            'time.google.com',
            'pool.ntp.org', 
            'time.nist.gov',
            'time.windows.com'
        ]
        
        for server in ntp_servers:
            try:
                client = ntplib.NTPClient()
                response = client.request(server, version=3, timeout=5)
                ntp_timestamp = response.tx_time
                local_timestamp = time.time()
                
                _ntp_time_offset = ntp_timestamp - local_timestamp
                _last_ntp_sync = current_time
                
                ntp_time = datetime.fromtimestamp(ntp_timestamp)
                time_diff = abs(_ntp_time_offset)
                
                if time_diff > 2:
                    print_enhanced(f"⚠️ 시간 차이 감지: {time_diff:.1f}초 - NTP 동기화 적용 ({server})", "bright_yellow")
                elif force:
                    print_enhanced(f"🌐 NTP 시간 동기화 완료: {server} ({ntp_time.strftime('%Y-%m-%d %H:%M:%S')})", "bright_green")
                
                return True
                
            except Exception as e:
                print_enhanced(f"[NTP] ⚠️ {server} 실패: {e}", "red")
                continue
                
        if force:
            print_enhanced("⚠️ NTP 동기화 실패 - 로컬 시간 사용", "bright_red")
        return False
        
    except Exception as e:
        if force:
            print_enhanced(f"⚠️ 시간 동기화 오류: {e} - 로컬 시간 사용", "bright_red")
        return False

def get_ntp_time():
    """V2 방식: NTP 동기화된 시간 반환"""
    sync_ntp_time()
    return datetime.fromtimestamp(time.time() + _ntp_time_offset)

def is_market_time(current_time: datetime) -> Tuple[bool, str]:
    """🕐 장 시간 체크"""
    if current_time.weekday() >= 5:
        return False, f"주말입니다 ({current_time.strftime('%A')})"
    
    market_start = current_time.replace(hour=9, minute=0, second=0, microsecond=0)
    market_end = current_time.replace(hour=15, minute=30, second=0, microsecond=0)
    
    if current_time < market_start:
        time_to_start = market_start - current_time
        hours, remainder = divmod(time_to_start.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        return False, f"장 시작 전 (시작까지 {hours}시간 {minutes}분)"
    
    if current_time > market_end:
        return False, "장 마감 후"
    
    return True, "장 시간"

def is_trading_time(current_time: datetime) -> Tuple[bool, str]:
    """🕐 매매 가능 시간 체크"""
    is_market, market_msg = is_market_time(current_time)
    if not is_market:
        return False, market_msg
    
    trading_start = current_time.replace(hour=9, minute=5, second=0, microsecond=0)
    trading_end = current_time.replace(hour=14, minute=0, second=0, microsecond=0)
    
    if current_time < trading_start:
        time_to_start = trading_start - current_time
        minutes, seconds = divmod(time_to_start.seconds, 60)
        return False, f"매매 시작 전 ({minutes}분 {seconds}초 후 시작)"
    
    if current_time > trading_end:
        return False, "매매 시간 종료 (14:00 이후)"
    
    return True, "매매 가능 시간"

def is_force_sell_time(current_time: datetime) -> bool:
    """🕐 강제 청산 시간 체크"""
    force_sell_time = current_time.replace(hour=15, minute=10, second=0, microsecond=0)
    return current_time >= force_sell_time

def show_time_status():
    """🕐 Enhanced 시간 상태 표시"""
    sync_ntp_time(force=True)
    current_time = get_ntp_time()
    
    is_market, market_msg = is_market_time(current_time)
    is_trade, trade_msg = is_trading_time(current_time)
    is_force = is_force_sell_time(current_time)
    
    # Rich 테이블로 시간 상태 표시
    time_data = {
        "📅 현재 시간": current_time.strftime('%Y-%m-%d (%A) %H:%M:%S'),
        "🏢 장 상태": market_msg,
        "💰 매매 상태": trade_msg,
    }
    
    if is_force:
        time_data["🚨 강제 청산"] = "도달 (15:10 이후)"
    else:
        force_time = current_time.replace(hour=15, minute=10, second=0, microsecond=0)
        time_to_force = force_time - current_time
        if time_to_force.days >= 0:
            hours, remainder = divmod(time_to_force.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            time_data["🚨 강제 청산까지"] = f"{hours}시간 {minutes}분"
    
    create_status_table("🕐 시간 상태 확인 (V2 NTP 시스템)", time_data)
    
    return current_time, is_trade

# ================================================================================
# 🆕 장 마감 사이클 기반 프로그레스 계산
# ================================================================================

def get_last_market_close(current_time: datetime) -> datetime:
    """마지막 장 마감 시간 계산"""
    # 현재 요일 확인 (0=월요일, 4=금요일, 5=토요일, 6=일요일)
    weekday = current_time.weekday()
    
    # 장 마감 시간 (15:30)
    market_close_time = current_time.replace(hour=15, minute=30, second=0, microsecond=0)
    
    # 오늘이 평일이고 장 마감 후라면
    if weekday < 5 and current_time >= market_close_time:
        return market_close_time
    
    # 오늘이 평일이고 장 시간 중이라면
    elif weekday < 5 and current_time < market_close_time:
        # 어제로 이동
        days_back = 1
        # 어제가 일요일이면 금요일로
        if weekday == 0:  # 월요일
            days_back = 3
    
    # 오늘이 토요일이면 금요일로
    elif weekday == 5:
        days_back = 1
    
    # 오늘이 일요일이면 금요일로
    elif weekday == 6:
        days_back = 2
    
    # 계산된 날짜의 15:30
    last_close = current_time - timedelta(days=days_back)
    return last_close.replace(hour=15, minute=30, second=0, microsecond=0)

def get_next_market_open(current_time: datetime) -> datetime:
    """다음 장 시작 시간 계산"""
    # 현재 요일 확인
    weekday = current_time.weekday()
    
    # 장 시작 시간 (09:00)
    market_open_time = current_time.replace(hour=9, minute=0, second=0, microsecond=0)
    
    # 오늘이 평일이고 장 시작 전이라면
    if weekday < 5 and current_time < market_open_time:
        return market_open_time
    
    # 그 외의 경우 다음 평일 계산
    days_ahead = 1
    
    # 금요일 장 시간 후 또는 토요일
    if weekday == 4 and current_time >= market_open_time:  # 금요일
        days_ahead = 3
    elif weekday == 5:  # 토요일
        days_ahead = 2
    elif weekday == 6:  # 일요일
        days_ahead = 1
    
    # 계산된 날짜의 09:00
    next_open = current_time + timedelta(days=days_ahead)
    return next_open.replace(hour=9, minute=0, second=0, microsecond=0)

def calculate_market_cycle_progress(current_time: datetime) -> Tuple[float, timedelta, timedelta]:
    """장 마감 사이클 진행률 계산"""
    last_close = get_last_market_close(current_time)
    next_open = get_next_market_open(current_time)
    
    # 전체 사이클 시간 (마지막 장 마감 ~ 다음 장 시작)
    total_cycle = (next_open - last_close).total_seconds()
    
    # 경과 시간
    elapsed = (current_time - last_close).total_seconds()
    
    # 진행률 (0 ~ 100)
    progress = min(max(elapsed / total_cycle * 100, 0), 100)
    
    # 남은 시간
    time_remaining = next_open - current_time
    
    return progress, time_remaining, next_open - last_close

# ================================================================================
# 🆕 Enhanced 장시작 대기 카운트다운 (전체 사이클 기반)
# ================================================================================

async def wait_for_market_open(ntp_time_func, test_mode=False):
    """🕐 장시작 대기 카운트다운 (Enhanced UI with Full Cycle Progress)"""
    
    if test_mode:
        return True  # 테스트 모드는 즉시 진행
    
    # 색상 설정
    if COLORAMA_AVAILABLE:
        color_red = Fore.RED
        color_yellow = Fore.YELLOW
        color_green = Fore.GREEN
        color_cyan = Fore.CYAN
        color_white = Fore.WHITE
        color_bright_yellow = Fore.LIGHTYELLOW_EX
        color_bright_green = Fore.LIGHTGREEN_EX
        color_magenta = Fore.MAGENTA
        color_reset = Style.RESET_ALL
    else:
        color_red = color_yellow = color_green = color_cyan = color_white = ""
        color_bright_yellow = color_bright_green = color_magenta = color_reset = ""
    
    # Rich Live 디스플레이 준비
    if RICH_AVAILABLE:
        from rich.live import Live
        from rich.layout import Layout
        from rich.table import Table
        
    while True:
        current_time = ntp_time_func()
        
        # 매매 시작 시간 (09:05)
        trading_start = current_time.replace(hour=9, minute=5, second=0, microsecond=0)
        
        # 현재 시간이 매매 시간이면 즉시 반환
        if current_time >= trading_start:
            if current_time.hour < 14:  # 14시 이전이면 매매 가능
                return True
            else:
                print_enhanced("⚠️ 매매 시간(09:05~14:00)이 종료되었습니다.", "red")
                return False
        
        # Rich를 사용한 고정 화면 업데이트
        if RICH_AVAILABLE:
            with Live(console=console, refresh_per_second=1, transient=True) as live:
                while True:
                    current_time = ntp_time_func()
                    
                    # 매매 시작 시간 체크
                    if current_time >= trading_start:
                        if current_time.hour < 14:
                            live.stop()
                            return True
                        else:
                            live.stop()
                            print_enhanced("⚠️ 매매 시간(09:05~14:00)이 종료되었습니다.", "red")
                            return False
                    
                    # 프로그레스 및 시간 계산
                    progress, time_remaining, total_cycle = calculate_market_cycle_progress(current_time)
                    last_close = get_last_market_close(current_time)
                    next_open = get_next_market_open(current_time)
                    
                    # 남은 시간 계산
                    total_seconds = int(time_remaining.total_seconds())
                    days = total_seconds // 86400
                    hours = (total_seconds % 86400) // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    
                    # 메시지 결정
                    if days > 0:
                        main_message = f"🕐 장시작까지 {days}일 {hours}시간 {minutes}분 남음"
                        rich_style = "yellow"
                    elif hours >= 1:
                        main_message = f"🕐 장시작까지 {hours}시간 {minutes}분 남음"
                        rich_style = "yellow"
                    elif minutes >= 30:
                        main_message = f"🕐 장시작까지 {minutes}분 남음"
                        rich_style = "bright_yellow"
                    elif minutes >= 10:
                        main_message = f"⏰ 장시작까지 {minutes}분 남음"
                        rich_style = "cyan"
                        
                        # 토큰 체크 (8:50~8:55)
                        if current_time.hour == 8 and 50 <= current_time.minute <= 55:
                            # 토큰 체크는 별도로 처리 (한 번만)
                            pass
                    else:
                        main_message = f"🚨 장시작까지 {minutes}분 {seconds}초!"
                        rich_style = "bright_green"
                    
                    # 레이아웃 구성
                    layout = Layout()
                    
                    # 시간 정보 패널
                    time_panel = Panel(
                        f"현재 시간: {current_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"마지막 장 마감: {last_close.strftime('%m/%d %H:%M')} "
                        f"({'금요일' if last_close.weekday() == 4 else '어제'})\n"
                        f"다음 장 시작: {next_open.strftime('%m/%d %H:%M')} "
                        f"({'월요일' if next_open.weekday() == 0 else '오늘'})\n"
                        f"전체 사이클: {int(total_cycle.total_seconds()/3600)}시간\n"
                        f"{main_message}",
                        title="⏰ 장 마감 사이클 진행 상황",
                        style=rich_style
                    )
                    
                    # 프로그레스 바
                    progress_bar = Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        BarColumn(),
                        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                        TimeElapsedColumn(),
                    )
                    task = progress_bar.add_task("장 마감 → 장 시작", total=100)
                    progress_bar.update(task, completed=progress)
                    
                    # 주말 메시지
                    weekend_msg = ""
                    if current_time.weekday() >= 5:
                        weekend_day = "토요일" if current_time.weekday() == 5 else "일요일"
                        weekend_msg = f"\n🌴 현재 {weekend_day}입니다. 월요일 장 시작을 기다리는 중..."
                    
                    # 전체 레이아웃 구성
                    full_display = Layout()
                    full_display.split_column(
                        Layout(time_panel),
                        Layout(progress_bar, size=3),
                        Layout(Text(weekend_msg, style="cyan") if weekend_msg else Text(""))
                    )
                    
                    # 화면 업데이트
                    live.update(full_display)
                    
                    # 토큰 체크 시간대 처리 (한 번만)
                    if current_time.hour == 8 and current_time.minute == 50 and current_time.second < 2:
                        live.stop()
                        print_enhanced("🔄 토큰 상태 확인 중...", "cyan")
                        should_refresh, reason = should_refresh_token()
                        if should_refresh:
                            print_enhanced(f"🔄 토큰 재발급: {reason}", "yellow")
                        # Live 재시작
                        live = Live(console=console, refresh_per_second=1, transient=True)
                        live.start()
                    
                    # 9시가 되면 특별 처리
                    if current_time.hour == 9 and current_time.minute == 0 and current_time.weekday() < 5:
                        live.stop()
                        print_enhanced("\n🎉 장이 시작되었습니다! 5분 후 매매를 시작합니다.", "bright_green")
                        
                        # 9:00 ~ 9:05 카운트다운
                        for i in range(300, 0, -1):
                            minutes_left = i // 60
                            seconds_left = i % 60
                            
                            if i % 30 == 0:
                                print_enhanced(f"⏳ 매매 시작까지 {minutes_left}분 {seconds_left}초 남음", "cyan")
                            
                            await asyncio.sleep(1)
                        
                        return True
                    
                    await asyncio.sleep(1)
        
        else:
            # Rich가 없는 경우 기존 방식 (개선)
            import os
            
            while True:
                current_time = ntp_time_func()
                
                # 매매 시작 시간 체크
                if current_time >= trading_start:
                    if current_time.hour < 14:
                        return True
                    else:
                        print_enhanced("⚠️ 매매 시간(09:05~14:00)이 종료되었습니다.", "red")
                        return False
                
                # 화면 클리어 (Windows)
                if os.name == 'nt':
                    os.system('cls')
                else:
                    os.system('clear')
                
                # 프로그레스 및 시간 계산
                progress, time_remaining, total_cycle = calculate_market_cycle_progress(current_time)
                last_close = get_last_market_close(current_time)
                next_open = get_next_market_open(current_time)
                
                # 남은 시간 계산
                total_seconds = int(time_remaining.total_seconds())
                days = total_seconds // 86400
                hours = (total_seconds % 86400) // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                
                # 메시지 및 색상 결정
                if days > 0:
                    main_message = f"🕐 장시작까지 {days}일 {hours}시간 {minutes}분 남음"
                    color = color_yellow
                elif hours >= 1:
                    main_message = f"🕐 장시작까지 {hours}시간 {minutes}분 남음"
                    color = color_yellow
                elif minutes >= 30:
                    main_message = f"🕐 장시작까지 {minutes}분 남음"
                    color = color_bright_yellow
                elif minutes >= 10:
                    main_message = f"⏰ 장시작까지 {minutes}분 남음"
                    color = color_cyan
                else:
                    main_message = f"🚨 장시작까지 {minutes}분 {seconds}초!"
                    color = color_bright_green
                
                # 출력
                print(f"\n{'='*70}")
                print(f"{color_white}📅 현재 시간: {current_time.strftime('%Y-%m-%d %H:%M:%S')}{color_reset}")
                print(f"{color_white}📉 마지막 장 마감: {last_close.strftime('%m/%d %H:%M')} "
                      f"({'금요일' if last_close.weekday() == 4 else '어제'}){color_reset}")
                print(f"{color_white}📈 다음 장 시작: {next_open.strftime('%m/%d %H:%M')} "
                      f"({'월요일' if next_open.weekday() == 0 else '오늘'}){color_reset}")
                print(f"{color_magenta}⏱️ 전체 사이클: {int(total_cycle.total_seconds()/3600)}시간{color_reset}")
                print(f"{color}{main_message}{color_reset}")
                
                # 텍스트 프로그레스 바
                bar_length = 50
                filled_length = int(bar_length * progress // 100)
                bar = '█' * filled_length + '░' * (bar_length - filled_length)
                
                print(f"\n진행률: [{bar}] {progress:5.1f}%")
                print(f"{'='*70}")
                
                # 주말 특별 메시지
                if current_time.weekday() >= 5:
                    weekend_day = "토요일" if current_time.weekday() == 5 else "일요일"
                    print(f"\n{color_cyan}🌴 현재 {weekend_day}입니다. 월요일 장 시작을 기다리는 중...{color_reset}")
                
                # 1초 대기
                await asyncio.sleep(1)

# ================================================================================
# 🔄 Enhanced 카운트다운 대기 시스템
# ================================================================================

async def enhanced_countdown_wait(seconds: int, test_mode: bool = False, engine=None):
    """🎨 Enhanced 카운트다운 대기 시스템"""
    
    start_time = get_ntp_time()
    
    if RICH_AVAILABLE:
        # Rich 프로그레스 바 사용
        with create_progress_bar(f"💤 {seconds}초 대기 중... [{start_time.strftime('%H:%M:%S')}]") as progress:
            task = progress.add_task("대기 중...", total=seconds)
            
            for elapsed in range(seconds + 1):
                if elapsed > 0:
                    await asyncio.sleep(1)
                    
                progress.update(task, advance=1)
                
                # 강제 청산 시간 체크 (15초마다)
                if not test_mode and elapsed % 15 == 0:
                    ntp_time = get_ntp_time()
                    if is_force_sell_time(ntp_time):
                        progress.stop()
                        print_enhanced("🚨 대기 중 강제 청산 시간 도달! 대기 중단...", "bright_red")
                        return True
        
        print_enhanced("✅ 대기 완료! 다음 루프 시작...", "bright_green")
    else:
        # 기본 카운트다운 (Colorama 사용)
        print_enhanced(f"\n💤 {seconds}초 대기 시작... [{start_time.strftime('%H:%M:%S')}]", "cyan")
        print("=" * 60)
        
        for i in range(seconds):
            await asyncio.sleep(1)
            remaining = seconds - i - 1
            progress = ((i + 1) / seconds) * 100
            
            # 프로그레스 바 생성
            bar_length = 30
            filled_length = int(bar_length * (i + 1) // seconds)
            bar = '█' * filled_length + '░' * (bar_length - filled_length)
            
            current_time = datetime.now()
            
            if COLORAMA_AVAILABLE:
                print(f"{Fore.YELLOW}⏰ [{current_time.strftime('%H:%M:%S')}] "
                      f"경과: {i+1:2d}초 | 남은시간: {remaining:2d}초 | "
                      f"[{Fore.GREEN}{bar}{Fore.YELLOW}] {progress:5.1f}%")
            else:
                print(f"⏰ [{current_time.strftime('%H:%M:%S')}] "
                      f"경과: {i+1:2d}초 | 남은시간: {remaining:2d}초 | "
                      f"[{bar}] {progress:5.1f}%")
            
            # 강제 청산 시간 체크
            if not test_mode and (i + 1) % 15 == 0:
                ntp_time = get_ntp_time()
                if is_force_sell_time(ntp_time):
                    print_enhanced("🚨 대기 중 강제 청산 시간 도달! 대기 중단...", "bright_red")
                    return True
        
        print_enhanced("✅ 대기 완료! 다음 루프 시작...", "bright_green")
        print("=" * 60)
    
    return False

# ================================================================================
# 🔧 Enhanced UI 매수 통합 함수
# ================================================================================

async def find_scalping_targets_enhanced(engine: ScalpingEngine, token: str, top_n: int = None) -> List[Dict]:
    """🎨 Enhanced UI 10만원 한도 기반 단타 매수 대상 검색"""
    all_candidates = []
    
    mode_text = "모니터링 전용" if engine.monitor_only else "실제 거래"
    
    # 시작 패널 표시
    if RICH_AVAILABLE:
        console.print(Panel(
            f"🔍 조건검색식 매수 대상 검색\n💡 모드: {mode_text}",
            title="📡 검색 시작",
            style="bright_blue"
        ))
    else:
        print_enhanced(f"\n🔍 조건검색식 매수 대상 검색 시작... [{mode_text}]", "bright_blue")
    
    # 조건검색 결과 테이블
    if RICH_AVAILABLE:
        results_table = Table(title="📋 조건검색식 결과", box=box.ROUNDED)
        results_table.add_column("조건번호", style="cyan", no_wrap=True)
        results_table.add_column("조건명", style="green")
        results_table.add_column("발견종목", style="yellow")
        results_table.add_column("유효종목", style="magenta")
        results_table.add_column("상태", style="white")
    
    for seq in CONDITION_SEQ_LIST:
        try:
            print_enhanced(f"\n📡 조건검색식 {seq}번 실행 중...", "cyan")
            codes, cond_name = await get_condition_codes(seq, token)
            
            if not codes:
                status = "❌ 결과 없음"
                if RICH_AVAILABLE:
                    results_table.add_row(str(seq), "조회 실패", "0", "0", status)
                print_enhanced(f"📝 조건검색식 {seq}번 결과 없음", "red")
                continue
            
            print_enhanced(f"✅ 조건검색식 {seq}번 ({cond_name}) - {len(codes)}개 종목 발견", "green")
            
            # 종목 정보 수집
            process_count = len(codes) if top_n is None else min(len(codes), top_n)
            candidates = []
            etf_count = 0
            api_fail_count = 0
            over_price_count = 0
            
            # Rich 프로그레스 바로 진행률 표시
            if RICH_AVAILABLE:
                with create_progress_bar(f"종목 정보 수집 중... (조건{seq})") as progress:
                    task = progress.add_task("처리 중...", total=process_count)
                    
                    for i, code in enumerate(codes[:process_count]):
                        if i > 0:
                            time.sleep(0.1)
                        
                        code = normalize_code(code)
                        info = get_stock_info(code, token)
                        
                        if not info:
                            api_fail_count += 1
                            progress.update(task, advance=1)
                            continue
                        
                        if is_etf_etn(info.get("name", "")):
                            etf_count += 1
                            progress.update(task, advance=1)
                            continue
                        
                        if info["price"] > 100_000:
                            over_price_count += 1
                            progress.update(task, advance=1)
                            continue
                        
                        candidate = {
                            "code": code,
                            "name": info["name"],
                            "price": info["price"],
                            "amount": info["amount"],
                            "condition_seq": seq,
                            "condition_name": cond_name
                        }
                        candidates.append(candidate)
                        progress.update(task, advance=1)
            else:
                # 기본 처리
                for i, code in enumerate(codes[:process_count]):
                    if i > 0:
                        time.sleep(0.1)
                    
                    code = normalize_code(code)
                    info = get_stock_info(code, token)
                    
                    if not info:
                        api_fail_count += 1
                        continue
                    
                    if is_etf_etn(info.get("name", "")):
                        etf_count += 1
                        continue
                    
                    if info["price"] > 100_000:
                        over_price_count += 1
                        continue
                    
                    candidate = {
                        "code": code,
                        "name": info["name"],
                        "price": info["price"],
                        "amount": info["amount"],
                        "condition_seq": seq,
                        "condition_name": cond_name
                    }
                    candidates.append(candidate)
            
            # 결과 정리
            candidates.sort(key=lambda x: x["amount"], reverse=True)
            status = f"✅ {len(candidates)}개 유효"
            
            if RICH_AVAILABLE:
                results_table.add_row(
                    str(seq), 
                    cond_name[:20] + "..." if len(cond_name) > 20 else cond_name,
                    str(len(codes)), 
                    str(len(candidates)), 
                    status
                )
            
            # 필터링 결과 출력
            filter_info = f"ETF제외: {etf_count}개, 주가초과: {over_price_count}개, API실패: {api_fail_count}개"
            print_enhanced(f"📊 필터링 결과: {process_count}개 처리 → {len(candidates)}개 유효 ({filter_info})", "yellow")
            
            all_candidates.extend(candidates)
                    
        except Exception as e:
            print_enhanced(f"[ERROR] 조건검색식 {seq} 조회 실패: {e}", "red")
            if RICH_AVAILABLE:
                results_table.add_row(str(seq), "오류 발생", "0", "0", "❌ 실패")
        
        time.sleep(0.5)
    
    # 조건검색 결과 테이블 출력
    if RICH_AVAILABLE:
        console.print(results_table)
    
    # 최종 후보 정리
    all_candidates.sort(key=lambda x: x["amount"], reverse=True)
    
    if not all_candidates:
        print_enhanced("📝 10만원 한도 내 매수 가능한 종목이 없습니다.", "red")
        return []
    
    # 최종 후보 테이블
    if RICH_AVAILABLE:
        final_table = Table(title="🎯 최종 매수 후보 (거래대금 순)", box=box.ROUNDED)
        final_table.add_column("순위", style="cyan", no_wrap=True)
        final_table.add_column("종목명", style="green")
        final_table.add_column("현재가", style="yellow", justify="right")
        final_table.add_column("예상수량", style="magenta", justify="right")
        final_table.add_column("예상금액", style="white", justify="right")
        final_table.add_column("조건", style="blue")
        
        for i, candidate in enumerate(all_candidates[:10], 1):
            max_quantity = 100_000 // candidate["price"]
            max_amount = max_quantity * candidate["price"]
            
            final_table.add_row(
                str(i),
                candidate['name'][:15] + "..." if len(candidate['name']) > 15 else candidate['name'],
                f"{candidate['price']:,}원",
                f"{max_quantity}주",
                f"{max_amount:,}원",
                f"조건{candidate['condition_seq']}"
            )
        
        console.print(final_table)
    else:
        print_enhanced(f"\n🎯 최종 후보: {len(all_candidates)}개 종목 (거래대금 순)", "bright_green")
        for i, candidate in enumerate(all_candidates[:5], 1):
            max_quantity = 100_000 // candidate["price"]
            max_amount = max_quantity * candidate["price"]
            status_text = "분석만" if engine.monitor_only else f"조건{candidate['condition_seq']}"
            print_enhanced(f"  {i}. {candidate['name']} @{candidate['price']:,}원 - {max_quantity}주 = {max_amount:,}원 ({status_text})", "white")
    
    # 스마트 자동 매수 실행
    if not engine.monitor_only:
        current_positions = len(engine.positions)
        available_positions = 5 - current_positions
        
        if available_positions > 0:
            if RICH_AVAILABLE:
                console.print(Panel(
                    f"🎯 목표: {available_positions}개 종목 (현재: {current_positions}/5)\n💰 종목당 한도: 100,000원",
                    title="🚀 스마트 자동 매수 시작",
                    style="bright_green"
                ))
            else:
                print_enhanced(f"\n🚀 스마트 자동 매수 시작:", "bright_green")
                print_enhanced(f"   🎯 목표: {available_positions}개 종목 (현재: {current_positions}/5)", "white")
            
            bought_count = engine.buy_available_stocks_smartly(all_candidates, available_positions)
            
            if bought_count > 0:
                print_enhanced(f"✅ 스마트 매수 성공: {bought_count}개 종목", "bright_green")
                
                # 데이터 저장
                try:
                    save_result = engine.money_manager.save_daily_data()
                    print_enhanced(f"💾 거래 데이터 저장 완료: {save_result}", "green")
                except Exception as save_error:
                    print_enhanced(f"⚠️ 데이터 저장 실패: {save_error}", "red")
                
                # 매수 후 상태 출력
                if engine.positions:
                    print_detailed_positions_table_enhanced(engine, token)
            else:
                print_enhanced("❌ 매수 실패: 모든 후보 종목 매수 불가", "red")
        else:
            print_enhanced(f"\n⚠️ 포지션 한도 초과: {current_positions}/5 - 매수 건너뜀", "yellow")
    else:
        print_enhanced("\n👀 [모니터링 전용] 실제 매수 없이 분석만 완료", "cyan")
        available_positions = 5
        analyze_count = engine.buy_available_stocks_smartly(all_candidates, available_positions)
        print_enhanced(f"👀 분석 완료: {analyze_count}개 종목 분석", "cyan")
    
    return all_candidates

def print_detailed_positions_table_enhanced(engine: ScalpingEngine, token: str):
    """🎨 Enhanced 상세 포지션 현황 테이블"""
    
    if not engine.positions:
        print_enhanced("[INFO] 📝 현재 보유 포지션이 없습니다.", "yellow")
        return
    
    if RICH_AVAILABLE:
        table = Table(title=f"📊 실시간 포지션 상세 현황 ({len(engine.positions)}개)", box=box.ROUNDED)
        table.add_column("순번", style="cyan", no_wrap=True)
        table.add_column("종목명", style="green")
        table.add_column("매수가", style="yellow", justify="right")
        table.add_column("현재가", style="white", justify="right")
        table.add_column("수익률", style="magenta", justify="right")
        table.add_column("보유시간", style="blue")
        table.add_column("상태", style="white")
        
        total_cost = 0
        total_current_value = 0
        total_profit = 0
        
        for i, pos in enumerate(engine.positions, 1):
            try:
                current_price = get_current_price(pos.code, token)
                
                if current_price > 0:
                    current_value = pos.get_current_value(current_price)
                    profit_amount, profit_rate = pos.get_profit_loss(current_price)
                    
                    total_cost += pos.cost
                    total_current_value += current_value
                    total_profit += profit_amount
                    
                    # 보유 시간 계산
                    hold_duration = datetime.now() - pos.buy_time
                    hold_minutes = int(hold_duration.total_seconds() / 60)
                    hold_time_str = f"{hold_minutes}분" if hold_minutes < 60 else f"{hold_minutes//60}시간{hold_minutes%60}분"
                    
                    # 상태 결정
                    if profit_rate >= 4.5:
                        status = "🟢 익절임박"
                        row_style = "green"
                    elif profit_rate >= 2.0:
                        status = "🟢 수익확대"
                        row_style = "green"
                    elif profit_rate > 0:
                        status = "🟢 수익"
                        row_style = "green"
                    elif profit_rate >= -2.0:
                        status = "⚪ 소폭손실"
                        row_style = "white"
                    elif profit_rate >= -4.5:
                        status = "🔴 손실확대"
                        row_style = "red"
                    else:
                        status = "🔴 손절임박"
                        row_style = "red"
                    
                    table.add_row(
                        str(i),
                        pos.name[:12] + "..." if len(pos.name) > 12 else pos.name,
                        f"{pos.buy_price:,}",
                        f"{current_price:,}",
                        f"{profit_rate:+.2f}%",
                        hold_time_str,
                        status,
                        style=row_style
                    )
                else:
                    table.add_row(
                        str(i),
                        pos.name[:12] + "..." if len(pos.name) > 12 else pos.name,
                        f"{pos.buy_price:,}",
                        "조회실패",
                        "-",
                        "-",
                        "❓ 오류",
                        style="red"
                    )
            except Exception:
                table.add_row(
                    str(i),
                    pos.name[:12] + "..." if len(pos.name) > 12 else pos.name,
                    f"{pos.buy_price:,}",
                    "오류",
                    "-",
                    "-",
                    "❓ 오류",
                    style="red"
                )
        
        console.print(table)
        
        # 포트폴리오 요약
        if total_cost > 0:
            total_profit_rate = (total_profit / total_cost * 100)
            cumulative_return = engine.money_manager.cumulative_return
            
            summary_data = {
                "💼 투자금": f"{total_cost:,}원",
                "💎 평가금액": f"{total_current_value:,}원",
                "📊 평가손익": f"{total_profit:+,}원 ({total_profit_rate:+.2f}%)",
                "🎯 누적 수익률": f"{cumulative_return:+.2f}%"
            }
            
            create_status_table("💼 포트폴리오 종합", summary_data)
            
            # 알림
            near_profit = len([p for p in engine.positions if any("익절임박" in str(row) for row in table.rows)])
            near_loss = len([p for p in engine.positions if any("손절임박" in str(row) for row in table.rows)])
            
            if near_profit > 0:
                print_enhanced(f"🟢 익절 임박: {near_profit}개 종목 (+4.5% 이상)", "bright_green")
            if near_loss > 0:
                print_enhanced(f"🔴 손절 임박: {near_loss}개 종목 (-4.5% 이하)", "bright_red")
    else:
        # 기본 테이블 출력
        print_enhanced(f"\n📊 [실시간 포지션 상세 현황] {len(engine.positions)}개", "bright_blue")
        # 기존 tabulate 방식 유지
        print_detailed_positions_table(engine, token)

# ================================================================================
# 🔄 Enhanced 메인 거래 루프
# ================================================================================

async def main_trading_loop_enhanced(test_mode: bool = False, monitor_only: bool = False):
    """🎨 Enhanced 메인 거래 루프"""
    
    try:
        # 토큰 검증
        token = ensure_token_for_full_trading_day()
        
        # 엔진 생성
        engine = ScalpingEngine(monitor_only=monitor_only)
        
        # 시간 상태 확인
        server_time, can_trade = show_time_status()
        
        if not test_mode and not monitor_only and not can_trade:
            print_enhanced("\n⚠️ 현재 매매 가능 시간이 아닙니다.", "red")
            print_enhanced("💡 테스트 모드로 실행하려면 메뉴에서 '2'를 선택하세요.", "yellow")
            return
        
        # 모드 알림
        if test_mode and not monitor_only:
            print_enhanced("\n🧪 [테스트 모드] 시간 제약 없이 실행합니다.", "bright_yellow")
        elif monitor_only:
            print_enhanced("\n👀 [모니터링 전용] 실제 매수/매도 없이 조건검색 결과만 분석합니다.", "bright_cyan")
        
        # 루프 간격 설정
        loop_interval = 30 if test_mode else 60
        
        # 시작 정보 패널
        mode_title = "조건검색 모니터링 시스템" if monitor_only else "10만원 한도 스캘핑 시스템"
        
        start_info = {
            "📅 시작 시간": server_time.strftime('%Y-%m-%d %H:%M:%S'),
            "🧪 테스트 모드": 'ON' if test_mode else 'OFF',
            "👀 모니터링 전용": 'ON' if monitor_only else 'OFF',
            "⏰ 루프 간격": f"{loop_interval}초",
            "🌐 시간 서버": "V2 NTP 시스템",
            "💰 시스템 설정": "50만원 가상자산, 종목당 10만원 한도, 최대 5종목"
        }
        
        if RICH_AVAILABLE:
            console.print(Panel(
                "\n".join([f"{k}: {v}" for k, v in start_info.items()]),
                title=f"🚀 {mode_title} V3.4 시작!",
                style="bright_green"
            ))
        else:
            print_enhanced(f"\n🚀 {mode_title} V3.4 시작!", "bright_green")
            for k, v in start_info.items():
                print_enhanced(f"  {k}: {v}", "white")
        
        # 초기 상태 출력
        if not monitor_only:
            engine.print_status()
        
        # 시스템 특징 설명
        if monitor_only:
            features = [
                "🔍 조건검색 결과만 분석",
                "❌ 실제 매수/매도 없음",
                "📊 수익률 변화 없음",
                "💰 자금 변화 없음"
            ]
        else:
            features = [
                "❌ 주가 10만원 초과 종목 → 완전 패스",
                "✅ 주가 10만원 이하 종목 → 한도 내 최대 매수",
                "🔄 수량 제한 없음 (1주든 100주든 상관없음)",
                "🎯 매수 실패 시 자동으로 다음 종목 시도",
                "📊 VirtualMoneyManager 완전 연동",
                "💾 실시간 데이터 저장 보장"
            ]
        
        if RICH_AVAILABLE:
            console.print(Panel(
                "\n".join(features),
                title="💡 시스템 특징",
                style="cyan"
            ))
        else:
            print_enhanced("\n💡 시스템 특징:", "cyan")
            for feature in features:
                print_enhanced(f"  • {feature}", "white")
        
        loop_count = 0
        
        # 메인 거래 루프
        while True:
            loop_count += 1
            loop_start_time = time.time()
            
            try:
                current_server_time = get_ntp_time()
                mode_text = "모니터링 전용" if monitor_only else "실제 거래"
                
                # 루프 시작 알림
                if RICH_AVAILABLE:
                    console.print(Panel(
                        f"시간: {current_server_time.strftime('%H:%M:%S')}\n모드: {mode_text}",
                        title=f"🔄 거래 루프 {loop_count}",
                        style="bright_blue"
                    ))
                else:
                    print_enhanced(f"\n🔄 거래 루프 {loop_count} 시작 ({current_server_time.strftime('%H:%M:%S')}) [{mode_text}]", "bright_blue")
                
                # 강제 청산 시간 체크
                if not test_mode and not monitor_only and is_force_sell_time(current_server_time):
                    print_enhanced("🚨 강제 청산 시간 도달 (15:10)", "bright_red")
                    force_count = engine.force_sell_all(token)
                    if force_count > 0:
                        print_enhanced(f"🚨 강제 청산 실행: {force_count}개", "bright_red")
                        
                        # 데이터 저장
                        try:
                            save_result = engine.money_manager.save_daily_data()
                            print_enhanced(f"💾 강제 청산 후 데이터 저장: {save_result}", "green")
                        except Exception as save_error:
                            print_enhanced(f"⚠️ 강제 청산 후 데이터 저장 실패: {save_error}", "red")
                    else:
                        print_enhanced("📝 강제 청산할 포지션이 없습니다.", "yellow")
                    
                    print_enhanced("🏁 거래 종료 - 장 마감", "bright_green")
                    break
                
                # 매매 시간 재확인
                if not test_mode and not monitor_only:
                    can_trade_now, trade_status = is_trading_time(current_server_time)
                    if not can_trade_now:
                        print_enhanced(f"⚠️ 매매 시간 종료: {trade_status}", "red")
                        print_enhanced("🏁 거래 루프 종료", "bright_green")
                        break
                
                # 매수 대상 검색 (Enhanced UI)
                candidates = await find_scalping_targets_enhanced(engine, token, top_n=None)
                
                # 청산 조건 체크
                if not monitor_only and engine.positions:
                    print_enhanced("\n🔍 청산 조건 체크 중...", "cyan")
                    exit_count = engine.check_exit_conditions(token)
                    if exit_count > 0:
                        engine.log_activity(f"✅ 청산 완료: {exit_count}개 포지션")
                        
                        # 데이터 저장
                        try:
                            save_result = engine.money_manager.save_daily_data()
                            engine.log_activity(f"💾 청산 후 데이터 저장: {save_result}")
                        except Exception as save_error:
                            engine.log_activity(f"⚠️ 청산 후 데이터 저장 실패: {save_error}")
                        
                        # 청산 후 상태 업데이트
                        if engine.positions:
                            print_detailed_positions_table_enhanced(engine, token)
                        else:
                            engine.print_status(token)
                    else:
                        print_enhanced("   📌 청산 조건 미충족 - 모든 포지션 유지", "yellow")
                        
                        if engine.positions:
                            print_detailed_positions_table_enhanced(engine, token)
                elif monitor_only:
                    print_enhanced("\n👀 [모니터링 전용] 실제 매수/매도 없음 - 조건검색 결과만 분석", "cyan")
                else:
                    print_enhanced("\n📊 현재 보유 포지션 없음", "yellow")
                
                # 데이터 저장 보장
                if not monitor_only and (len(engine.money_manager.all_buy_transactions) > 0 or len(engine.money_manager.all_sell_transactions) > 0):
                    try:
                        save_result = engine.money_manager.save_daily_data()
                        if loop_count % 10 == 0:
                            engine.log_activity(f"💾 루프 종료 시 데이터 저장: {save_result}")
                    except Exception as save_error:
                        engine.log_activity(f"⚠️ 루프 종료 시 데이터 저장 실패: {save_error}")
                
                # 루프 실행 시간
                loop_duration = time.time() - loop_start_time
                print_enhanced(f"\n⏱️ 루프 실행시간: {loop_duration:.2f}초", "white")
                
                # Enhanced 카운트다운 대기
                force_exit = await enhanced_countdown_wait(loop_interval, test_mode or monitor_only, engine)
                if force_exit:
                    print_enhanced("🚨 강제 청산 시간 도달로 루프 종료", "bright_red")
                    break
                
            except Exception as e:
                engine.log_activity(f"❌ 거래 루프 {loop_count} 오류: {e}")
                import traceback
                traceback.print_exc()
                print_enhanced(f"⚠️ 오류 발생, {loop_interval}초 후 재시도...", "red")
                
                await enhanced_countdown_wait(loop_interval, test_mode or monitor_only, engine)
            
    except KeyboardInterrupt:
        print_enhanced("\n\n👋 사용자가 프로그램을 종료했습니다.", "bright_yellow")
        
        if not monitor_only and 'engine' in locals() and engine.positions:
            print_enhanced(f"⚠️ 현재 {len(engine.positions)}개 포지션을 보유 중입니다.", "yellow")
            print_enhanced("💡 다음에 프로그램을 시작하면 기존 포지션을 확인할 수 있습니다.", "cyan")
    except Exception as e:
        print_enhanced(f"❌ 메인 루프 치명적 오류: {e}", "bright_red")
        import traceback
        traceback.print_exc()
    finally:
        print_enhanced("\n🧹 프로그램 종료 처리 중...", "cyan")
        
        try:
            if not monitor_only and 'engine' in locals():
                final_save = engine.money_manager.save_daily_data()
                print_enhanced(f"💾 최종 거래 데이터 저장 완료: {final_save}", "green")
                
                total_buy = len(engine.money_manager.all_buy_transactions)
                total_sell = len(engine.money_manager.all_sell_transactions)
                print_enhanced(f"📊 최종 거래 통계: 매수 {total_buy}회, 매도 {total_sell}회", "white")
                
        except Exception as e:
            print_enhanced(f"⚠️ 최종 데이터 저장 실패: {e}", "red")
        
        print_enhanced("✅ 프로그램 종료 완료", "bright_green")

# ================================================================================
# 🎯 Enhanced 메인 메뉴 시스템
# ================================================================================

async def enhanced_main():
    """🎨 Enhanced 메인 메뉴 시스템"""
    
    # 타이틀 표시
    if RICH_AVAILABLE:
        title_text = Text("🔥 V3.4 Enhanced Scalping System", style="bold bright_green")
        console.print(Panel(
            Align.center(title_text),
            subtitle="10만원 한도 내 수량 제한 없는 스캘핑 시스템 + Enhanced UI",
            style="bright_blue"
        ))
    else:
        print_enhanced("🔥 V3.4 Enhanced Scalping System", "bright_green")
        print_enhanced("10만원 한도 내 수량 제한 없는 스캘핑 시스템 + Enhanced UI", "cyan")
    
    # 시간 상태 표시
    server_time, can_trade = show_time_status()
    
    # 메뉴 옵션
    menu_options = [
        "1. 👀 모니터링 전용 모드 (조건검색 결과만, 실제 거래 없음)",
        "2. 🧪 테스트 모드 (30초 간격, 시간 제약 없음, 실제 가상거래)",
        "3. 💰 실전 매매 모드 (60초 간격, 시간 제약 있음)",
        "4. 🕐 시간 상태만 확인",
        "0. 🚪 종료"
    ]
    
    system_settings = [
        "• 가상 자산: 500,000원",
        "• 종목당 한도: 100,000원 (고정)",
        "• 최대 종목: 5개 (고정)",
        "• 주가 10만원 초과 → 자동 패스",
        "• 주가 10만원 이하 → 한도 내 최대 매수",
        "• 💾 자동 데이터 저장 (매수/매도/청산 시)"
    ]
    
    mode_descriptions = [
        "1번: 조건검색 결과만 분석, 수익률 변화 없음",
        "2번: 시간 상관없이 실제 가상거래, 수익률 변화 있음",
        "3번: 장시간에만 실제 거래"
    ]
    
    if RICH_AVAILABLE:
        # Rich 메뉴 표시
        console.print(Panel(
            "\n".join(menu_options),
            title="📋 실행 모드 선택",
            style="cyan"
        ))
        
        console.print(Panel(
            "\n".join(system_settings),
            title="💰 시스템 설정",
            style="green"
        ))
        
        console.print(Panel(
            "\n".join(mode_descriptions),
            title="💡 모드 설명",
            style="yellow"
        ))
    else:
        print_enhanced("\n📋 실행 모드 선택:", "cyan")
        for option in menu_options:
            print_enhanced(f"  {option}", "white")
        
        print_enhanced("\n💰 시스템 설정:", "green")
        for setting in system_settings:
            print_enhanced(f"  {setting}", "white")
        
        print_enhanced("\n💡 모드 설명:", "yellow")
        for desc in mode_descriptions:
            print_enhanced(f"  {desc}", "white")
    
    try:
        choice = input(f"\n선택하세요 (0-4): ").strip()
        
        if choice == '0':
            print_enhanced("👋 프로그램을 종료합니다.", "bright_green")
            return
        elif choice == '1':
            if RICH_AVAILABLE:
                console.print(Panel(
                    "• 조건검색 결과만 분석\n• 실제 매수/매도 없음\n• 수익률 변화 없음\n• 루프 간격: 30초",
                    title="👀 모니터링 전용 모드 선택됨",
                    style="bright_cyan"
                ))
            else:
                print_enhanced("\n👀 [모니터링 전용 모드] 선택됨", "bright_cyan")
            
            input("계속하려면 Enter를 누르세요...")
            await main_trading_loop_enhanced(test_mode=True, monitor_only=True)
            
        elif choice == '2':
            if RICH_AVAILABLE:
                console.print(Panel(
                    "• 루프 간격: 30초 (5초 간격 업데이트)\n• 시간 제약: 없음\n• 실제 가상거래 진행\n• V2 NTP 시스템 사용\n• 10만원 한도 적용\n• 💾 자동 데이터 저장",
                    title="🧪 테스트 모드 선택됨",
                    style="bright_yellow"
                ))
            else:
                print_enhanced("\n🧪 [테스트 모드] 선택됨", "bright_yellow")
            
            input("계속하려면 Enter를 누르세요...")
            await main_trading_loop_enhanced(test_mode=True, monitor_only=False)
            
        elif choice == '3':
            if RICH_AVAILABLE:
                console.print(Panel(
                    "• 루프 간격: 60초 (5초 간격 업데이트)\n• 시간 제약: 엄격 적용\n• V2 NTP 시스템 사용\n• 10만원 한도 적용\n• 💾 자동 데이터 저장",
                    title="💰 실전 매매 모드 선택됨",
                    style="bright_green"
                ))
            else:
                print_enhanced("\n💰 [실전 매매 모드] 선택됨", "bright_green")
            
            # 현재 시간 체크
            current_time = get_ntp_time()
            is_trade, trade_msg = is_trading_time(current_time)
            
            if not is_trade:
                print_enhanced(f"⚠️ {trade_msg}", "yellow")
                
                # 매매 시작 전이면 카운트다운 시작
                if current_time.hour < 9 or (current_time.hour == 9 and current_time.minute < 5):
                    print_enhanced("\n🕐 장시작 대기 모드로 진입합니다...", "cyan")
                    
                    # 장 마감 사이클 진행 상황 표시
                    progress, time_remaining, total_cycle = calculate_market_cycle_progress(current_time)
                    last_close = get_last_market_close(current_time)
                    next_open = get_next_market_open(current_time)
                    
                    print_enhanced(f"📉 마지막 장 마감: {last_close.strftime('%m/%d %H:%M')}", "white")
                    print_enhanced(f"📈 다음 장 시작: {next_open.strftime('%m/%d %H:%M')}", "white")
                    print_enhanced(f"⏱️ 전체 사이클: {int(total_cycle.total_seconds()/3600)}시간", "magenta")
                    print_enhanced(f"📊 현재 진행률: {progress:.1f}%", "cyan")
                    
                    # 카운트다운 실행
                    ready = await wait_for_market_open(get_ntp_time)
                    
                    if ready:
                        print_enhanced("\n✅ 매매 준비 완료! 실전 거래를 시작합니다.", "bright_green")
                        input("계속하려면 Enter를 누르세요...")
                        await main_trading_loop_enhanced(test_mode=False, monitor_only=False)
                    else:
                        print_enhanced("\n❌ 매매 시간이 종료되었습니다.", "red")
                        return
                else:
                    # 14시 이후
                    print_enhanced("💡 내일 장시작 전에 다시 실행해주세요.", "yellow")
                    return
            else:
                # 이미 매매 시간
                input("계속하려면 Enter를 누르세요...")
                await main_trading_loop_enhanced(test_mode=False, monitor_only=False)
            
        elif choice == '4':
            print_enhanced("\n✅ 시간 상태 확인 완료", "bright_green")
            
            # 추가 정보 표시
            current_time = get_ntp_time()
            progress, time_remaining, total_cycle = calculate_market_cycle_progress(current_time)
            
            print_enhanced("\n📊 장 마감 사이클 정보:", "cyan")
            print_enhanced(f"  • 진행률: {progress:.1f}%", "white")
            print_enhanced(f"  • 남은 시간: {int(time_remaining.total_seconds()/3600)}시간 {int((time_remaining.total_seconds()%3600)/60)}분", "white")
            
            return
        else:
            print_enhanced("❌ 올바른 번호를 입력해주세요. (0-4)", "red")
            await enhanced_main()
            
    except KeyboardInterrupt:
        print_enhanced("\n👋 사용자가 프로그램을 종료했습니다.", "bright_yellow")
    except Exception as e:
        print_enhanced(f"❌ 메뉴 실행 오류: {e}", "red")
        import traceback
        traceback.print_exc()

# ================================================================================
# 프로그램 시작점
# ================================================================================

if __name__ == "__main__":
    try:
        # 초기 NTP 동기화
        print_enhanced("🌐 V2 NTP 시스템 초기화 중...", "cyan")
        sync_ntp_time(force=True)
        
        # 시스템 소개
        if RICH_AVAILABLE:
            intro_text = """
🔥 V3.4 Enhanced UI - 10만원 한도 스캘핑 시스템

💡 주요 특징:
• 1번: 모니터링 전용 (조건검색만, 수익률 변화 없음)
• 2번: 테스트 모드 (실제 가상거래, 시간 무시)
• 3번: 실전 모드 (장시간에만 실제 거래)
• 주가 10만원 초과 종목은 자동으로 패스
• 주가 10만원 이하 종목은 한도 내에서 최대한 매수
• 수량 제한 없음 (1주든 100주든 상관없음)
• 50만원 가상자산으로 안전한 백테스팅
• VirtualTransaction 클래스로 정확한 수익률 계산
• 💾 매수/매도/청산 시 자동 데이터 저장 보장

🎨 Enhanced UI 특징:
• Rich 라이브러리로 아름다운 테이블
• Colorama로 컬러풀한 출력
• 프로그레스 바 및 실시간 상태 표시
• 깔끔한 패널과 박스 디자인
• 🆕 장 마감 사이클 기반 프로그레스 (금요일 15:30 → 월요일 09:00)
            """
            
            console.print(Panel(
                intro_text.strip(),
                title="🚀 시스템 소개",
                style="bright_blue"
            ))
        else:
            print_enhanced("🔥 V3.4 Enhanced UI - 10만원 한도 스캘핑 시스템", "bright_green")
            print_enhanced("💡 주요 특징:", "cyan")
            features = [
                "• 1번: 모니터링 전용 (조건검색만, 수익률 변화 없음)",
                "• 2번: 테스트 모드 (실제 가상거래, 시간 무시)",
                "• 3번: 실전 모드 (장시간에만 실제 거래)",
                "• 주가 10만원 초과 종목은 자동으로 패스",
                "• 주가 10만원 이하 종목은 한도 내에서 최대한 매수",
                "• 수량 제한 없음 (1주든 100주든 상관없음)",
                "• 50만원 가상자산으로 안전한 백테스팅",
                "• VirtualTransaction 클래스로 정확한 수익률 계산",
                "• 💾 매수/매도/청산 시 자동 데이터 저장 보장",
                "• 🆕 장 마감 사이클 기반 프로그레스 (금요일 15:30 → 월요일 09:00)"
            ]
            for feature in features:
                print_enhanced(f"  {feature}", "white")
        
        asyncio.run(enhanced_main())
        
    except KeyboardInterrupt:
        print_enhanced("\n👋 프로그램이 정상적으로 종료되었습니다.", "bright_green")
    except Exception as e:
        print_enhanced(f"❌ 프로그램 실행 오류: {e}", "red")
        import traceback
        traceback.print_exc()