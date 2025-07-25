"""
🔥 V3.2 단타 매매 러너 - V2 방식 NTP 타임서버
Smart scalping runner with V2 NTP time system + Clean countdown
"""

import asyncio
import time
import ntplib
from datetime import datetime, timedelta
from scalping_engine import *

# ================================================================================
# 🕐 V2 방식 NTP 타임서버 시간 관리 시스템
# ================================================================================

# 글로벌 시간 관리 변수 (V2 방식)
_ntp_time_offset = 0  # NTP와 로컬 시간의 차이
_last_ntp_sync = 0    # 마지막 NTP 동기화 시각
_ntp_sync_interval = 3600  # 1시간마다 재동기화

def sync_ntp_time(force=False):
    """V2 방식: NTP 시간 동기화 (1시간마다 또는 강제 동기화)"""
    global _ntp_time_offset, _last_ntp_sync
    
    current_time = time.time()
    
    # 강제 동기화가 아니고, 마지막 동기화로부터 1시간이 지나지 않았으면 스킵
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
                
                # 동기화 성공 메시지 (조건부 출력)
                ntp_time = datetime.fromtimestamp(ntp_timestamp)
                time_diff = abs(_ntp_time_offset)
                
                if time_diff > 2:  # 2초 이상 차이날 때만 경고
                    print(f"⚠️  시간 차이 감지: {time_diff:.1f}초 - NTP 동기화 적용 ({server})")
                elif force:  # 강제 동기화일 때만 성공 메시지
                    print(f"🌐 NTP 시간 동기화 완료: {server} ({ntp_time.strftime('%Y-%m-%d %H:%M:%S')})")
                
                return True
                
            except Exception as e:
                print(f"[NTP] ⚠️ {server} 실패: {e}")
                continue
                
        # 모든 서버 실패 시
        if force:
            print("⚠️  NTP 동기화 실패 - 로컬 시간 사용")
        return False
        
    except Exception as e:
        if force:
            print(f"⚠️  시간 동기화 오류: {e} - 로컬 시간 사용")
        return False

def get_ntp_time():
    """V2 방식: NTP 동기화된 시간 반환 (효율적 버전)"""
    # 첫 동기화 또는 1시간마다 재동기화
    sync_ntp_time()
    
    # 오프셋을 적용한 현재 시간 반환
    return datetime.fromtimestamp(time.time() + _ntp_time_offset)

def is_market_time(current_time: datetime) -> Tuple[bool, str]:
    """🕐 장 시간 체크"""
    
    # 평일 체크 (월=0, 일=6)
    if current_time.weekday() >= 5:  # 토요일(5), 일요일(6)
        return False, f"주말입니다 ({current_time.strftime('%A')})"
    
    # 장 시간 체크 (09:00 ~ 15:30)
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
    """🕐 매매 가능 시간 체크 (09:05 ~ 14:00)"""
    
    is_market, market_msg = is_market_time(current_time)
    if not is_market:
        return False, market_msg
    
    # 매매 시간 체크 (09:05 ~ 14:00)
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
    """🕐 강제 청산 시간 체크 (15:10)"""
    force_sell_time = current_time.replace(hour=15, minute=10, second=0, microsecond=0)
    return current_time >= force_sell_time

def show_time_status():
    """🕐 현재 시간 상태 표시"""
    # 강제 동기화
    sync_ntp_time(force=True)
    current_time = get_ntp_time()
    
    print(f"\n{'='*70}")
    print(f"🕐 시간 상태 확인 (V2 NTP 시스템)")
    print(f"{'='*70}")
    print(f"📅 현재 시간: {current_time.strftime('%Y-%m-%d (%A) %H:%M:%S')}")
    
    is_market, market_msg = is_market_time(current_time)
    is_trade, trade_msg = is_trading_time(current_time)
    is_force = is_force_sell_time(current_time)
    
    print(f"🏢 장 상태: {market_msg}")
    print(f"💰 매매 상태: {trade_msg}")
    
    if is_force:
        print(f"🚨 강제 청산 시간: 도달 (15:10 이후)")
    else:
        force_time = current_time.replace(hour=15, minute=10, second=0, microsecond=0)
        time_to_force = force_time - current_time
        if time_to_force.days >= 0:
            hours, remainder = divmod(time_to_force.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            print(f"🚨 강제 청산까지: {hours}시간 {minutes}분")
    
    return current_time, is_trade

# ================================================================================
# 🔄 깔끔한 카운트다운 대기 시스템 (V2 NTP 적용)
# ================================================================================

async def clean_countdown_wait(seconds: int, test_mode: bool = False, engine=None):
    """🔄 깔끔한 카운트다운 대기 시스템 (V2 NTP 방식)"""
    
    # 시작 시간은 한 번만 조회
    start_time = get_ntp_time()
    print(f"\n💤 {seconds}초 대기 시작... [{start_time.strftime('%H:%M:%S')}]")
    print(f"{'='*60}")
    
    # 5초 간격으로 업데이트
    update_interval = 5
    total_updates = (seconds + update_interval - 1) // update_interval
    
    for i in range(total_updates):
        # 5초 대기 (마지막은 남은 시간만큼)
        if i == total_updates - 1:
            remaining_wait = seconds - (i * update_interval)
            if remaining_wait > 0:
                await asyncio.sleep(remaining_wait)
        else:
            await asyncio.sleep(update_interval)
        
        # 경과 시간 계산
        elapsed = min((i + 1) * update_interval, seconds)
        remaining = seconds - elapsed
        progress = (elapsed / seconds) * 100
        
        # 프로그레스 바 생성 (30칸)
        bar_length = 30
        filled_length = int(bar_length * elapsed // seconds)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        # 현재 시간 (로컬 시간 사용 - 매번 NTP 호출 안 함)
        current_time = datetime.now()
        
        # 상태 출력
        print(f"⏰ [{current_time.strftime('%H:%M:%S')}] "
              f"경과: {elapsed:2d}초 | 남은시간: {remaining:2d}초 | "
              f"[{bar}] {progress:5.1f}%")
        
        # 테스트 모드가 아닐 때 강제 청산 시간 체크 (15초마다만)
        if not test_mode and elapsed % 15 == 0:  # 15초마다만 NTP 체크
            ntp_time = get_ntp_time()
            if is_force_sell_time(ntp_time):
                print(f"🚨 대기 중 강제 청산 시간 도달! 대기 중단...")
                return True
        
        if elapsed >= seconds:
            break
    
    print(f"✅ 대기 완료! 다음 루프 시작...")
    print(f"{'='*60}")
    return False

# ================================================================================
# 🚀 스마트 매수 통합 함수
# ================================================================================

async def find_scalping_targets(engine: ScalpingEngine, token: str, top_n: int = None) -> List[Dict]:
    """🎯 단타 매수 대상 종목 검색 + 스마트 자동 매수 통합"""
    all_candidates = []
    
    print(f"\n🔍 조건검색식 매수 대상 검색 시작...", flush=True)
    
    # 🔍 기존 조건검색 로직 그대로 유지
    for seq in CONDITION_SEQ_LIST:
        try:
            print(f"\n📡 조건검색식 {seq}번 실행 중...", flush=True)
            codes, cond_name = await get_condition_codes(seq, token)
            
            if not codes:
                print(f"📝 조건검색식 {seq}번 결과 없음", flush=True)
                continue
            
            print(f"✅ 조건검색식 {seq}번 ({cond_name}) - {len(codes)}개 종목 발견", flush=True)
            
            # 처리할 종목 수 결정
            if top_n is None:
                process_count = len(codes)
                print(f"📊 전체 {process_count}개 종목 처리 중...", flush=True)
            else:
                process_count = min(len(codes), top_n)
                print(f"📊 상위 {process_count}개 종목 처리 중...", flush=True)
            
            # 종목 정보 수집 및 필터링 (기존 로직 그대로)
            candidates = []
            etf_count = 0
            api_fail_count = 0
            
            for i, code in enumerate(codes[:process_count]):
                if i > 0:
                    time.sleep(0.1)
                
                code = normalize_code(code)
                info = get_stock_info(code, token)
                
                if not info:
                    api_fail_count += 1
                    print(f"  ❌ API 실패: {code}", flush=True)
                    continue
                
                if is_etf_etn(info.get("name", "")):
                    etf_count += 1
                    print(f"  🚫 ETF/ETN 제외: {info.get('name', '')}({code})", flush=True)
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
                print(f"  ✅ 추가: {info['name']}({code}) - {info['amount']:,}원", flush=True)
            
            # 필터링 결과 요약
            print(f"📊 필터링 결과: {process_count}개 처리 → {len(candidates)}개 유효 "
                  f"(ETF제외: {etf_count}개, API실패: {api_fail_count}개)", flush=True)
            
            # 거래대금 순으로 정렬
            candidates.sort(key=lambda x: x["amount"], reverse=True)
            
            # 조건검색식 결과 테이블 표시
            print_condition_results_table(candidates, engine, seq, cond_name)
            
            # 매수 가능한 종목만 전체 후보에 추가
            for candidate in candidates:
                can_buy, reason = engine.can_buy_stock(candidate["code"])
                if can_buy:
                    all_candidates.append(candidate)
                    
        except Exception as e:
            print(f"[WARN] 조건검색식 {seq} 실행 실패: {e}", flush=True)
        
        time.sleep(0.5)
    
    # 전체 후보 거래대금 순으로 정렬
    all_candidates.sort(key=lambda x: x["amount"], reverse=True)
    
    if not all_candidates:
        print(f"\n📝 매수 가능한 종목이 없습니다.", flush=True)
        return []
    
    print(f"\n🎯 최종 매수 후보: {len(all_candidates)}개 종목 (거래대금 순)", flush=True)
    for i, candidate in enumerate(all_candidates[:5], 1):
        print(f"  {i}. {candidate['name']} - {candidate['amount']:,}원 (조건{candidate['condition_seq']})", flush=True)
    
    # 🚀 스마트 자동 매수 실행
    position_value, max_positions = engine.update_trading_strategy()
    current_positions = len(engine.positions)
    available_positions = max_positions - current_positions
    
    if available_positions > 0:
        print(f"\n🚀 스마트 자동 매수 시작:", flush=True)
        print(f"   🎯 목표: {available_positions}개 종목 (현재: {current_positions}/{max_positions})", flush=True)
        print(f"   💰 종목당 투자금액: {position_value:,}원", flush=True)
        
        # 🎯 가격대별 최적화된 순서로 재정렬
        optimized_candidates = engine.get_optimized_candidate_order(all_candidates)
        
        # 🚀 스마트 매수 실행 (실패 시 자동으로 다음 종목 시도)
        bought_count = engine.buy_available_stocks_smartly(optimized_candidates, available_positions)
        
        if bought_count > 0:
            print(f"✅ 스마트 매수 성공: {bought_count}개 종목", flush=True)
            
            # 매수 후 상태 출력
            if engine.positions:
                print_detailed_positions_table(engine, token)
        else:
            print(f"❌ 매수 실패: 모든 후보 종목 매수 불가", flush=True)
    else:
        print(f"\n⚠️ 포지션 한도 초과: {current_positions}/{max_positions} - 매수 건너뜀", flush=True)
    
    return all_candidates

# ================================================================================
# 🔄 메인 거래 루프 (V2 NTP 시스템)
# ================================================================================

async def main_trading_loop(test_mode: bool = False):
    """🔄 메인 거래 루프 (V2 NTP 시스템 + 깔끔한 카운트다운)"""
    
    try:
        # 🔑 토큰 검증
        token = ensure_token_for_full_trading_day()
        
        # 🔥 엔진 생성
        engine = ScalpingEngine()
        
        # 🕐 시간 상태 확인
        server_time, can_trade = show_time_status()
        
        if not test_mode and not can_trade:
            print(f"\n⚠️ 현재 매매 가능 시간이 아닙니다.")
            print(f"💡 테스트 모드로 실행하려면 메뉴에서 '1'을 선택하세요.")
            return
        
        if test_mode:
            print(f"\n🧪 [테스트 모드] 시간 제약 없이 실행합니다.")
        
        # 🚀 루프 간격 설정 (테스트 모드에서 더 빠르게)
        loop_interval = 30 if test_mode else 60  # 테스트: 30초, 실전: 60초
        
        # 🚀 시작 정보
        print(f"\n{'='*70}")
        print(f"🚀 스마트 자동 매수 스캘핑 시스템 V3.2 시작!")
        print(f"{'='*70}")
        print(f"📅 시작 시간: {server_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🧪 테스트 모드: {'ON' if test_mode else 'OFF'}")
        print(f"⏰ 루프 간격: {loop_interval}초 (5초 간격 업데이트)")
        print(f"🌐 시간 서버: V2 NTP 시스템 (ntplib)")
        
        # 초기 상태 출력
        engine.print_status()
        
        print(f"\n🚀 V3.2 스마트 자동 매수 특징:")
        print(f"   • 매수 실패 시 자동으로 다음 종목 시도")
        print(f"   • 가격대별 우선순위 최적화")
        print(f"   • VirtualMoneyManager 완전 연동")
        print(f"   • V2 방식 NTP 시간 동기화 (안정적)")
        print(f"   • 깔끔한 카운트다운 (5초 간격)")
        print(f"   • 실패 원인 분석 및 통계")
        
        loop_count = 0
        
        # 🔄 메인 거래 루프
        while True:
            loop_count += 1
            loop_start_time = time.time()
            
            try:
                current_server_time = get_ntp_time()
                print(f"\n🔄 거래 루프 {loop_count} 시작 ({current_server_time.strftime('%H:%M:%S')})")
                print(f"="*60)
                
                # ⚠️ 강제 청산 시간 체크 (V2 NTP 기준)
                if not test_mode and is_force_sell_time(current_server_time):
                    print("🚨 강제 청산 시간 도달 (15:10)")
                    force_count = engine.force_sell_all(token)
                    if force_count > 0:
                        print(f"🚨 강제 청산 실행: {force_count}개")
                    else:
                        print("📝 강제 청산할 포지션이 없습니다.")
                    
                    # 하루 마감 처리
                    engine.money_manager.finalize_day()
                    print("🏁 거래 종료 - 장 마감")
                    break
                
                # ⏰ 매매 시간 재확인 (V2 NTP 기준)
                if not test_mode:
                    can_trade_now, trade_status = is_trading_time(current_server_time)
                    if not can_trade_now:
                        print(f"⚠️ 매매 시간 종료: {trade_status}")
                        print("🏁 거래 루프 종료")
                        break
                
                # 🎯 스마트 매수 실행 (조건검색 + 최적화 + 자동 매수 통합)
                candidates = await find_scalping_targets(engine, token, top_n=None)
                
                # 🔍 청산 조건 체크
                if engine.positions:
                    print(f"\n🔍 청산 조건 체크 중...")
                    exit_count = engine.check_exit_conditions(token)
                    if exit_count > 0:
                        engine.log_activity(f"✅ 청산 완료: {exit_count}개 포지션")
                        
                        # 청산 후 상태 업데이트
                        if engine.positions:
                            print_detailed_positions_table(engine, token)
                        else:
                            engine.print_status(token)
                    else:
                        print(f"   📌 청산 조건 미충족 - 모든 포지션 유지")
                        
                        # 현재 포지션 상태 출력 (청산이 없을 때)
                        if engine.positions:
                            print_detailed_positions_table(engine, token)
                else:
                    print(f"\n📊 현재 보유 포지션 없음")
                
                # 루프 실행 시간 측정
                loop_duration = time.time() - loop_start_time
                print(f"\n⏱️ 루프 실행시간: {loop_duration:.2f}초")
                print(f"="*60)
                
                # 🔄 깔끔한 카운트다운 대기 (V2 NTP)
                force_exit = await clean_countdown_wait(loop_interval, test_mode, engine)
                if force_exit:
                    print("🚨 강제 청산 시간 도달로 루프 종료")
                    break
                
            except Exception as e:
                engine.log_activity(f"❌ 거래 루프 {loop_count} 오류: {e}")
                import traceback
                traceback.print_exc()
                print(f"⚠️ 오류 발생, {loop_interval}초 후 재시도...")
                
                # 오류 시에도 깔끔한 카운트다운
                await clean_countdown_wait(loop_interval, test_mode, engine)
            
    except KeyboardInterrupt:
        print(f"\n\n👋 사용자가 프로그램을 종료했습니다.")
        
        # 🚨 수동 종료 시 보유 포지션 처리
        if 'engine' in locals() and engine.positions:
            print(f"⚠️ 현재 {len(engine.positions)}개 포지션을 보유 중입니다.")
            print("💡 다음에 프로그램을 시작하면 기존 포지션을 확인할 수 있습니다.")
    except Exception as e:
        print(f"❌ 메인 루프 치명적 오류: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"\n🧹 프로그램 종료 처리 중...")
        
        # 최종 상태 저장
        try:
            if 'engine' in locals():
                engine.money_manager.save_daily_data()
                print("💾 오늘 거래 데이터 저장 완료")
        except Exception as e:
            print(f"⚠️ 데이터 저장 실패: {e}")
        
        print(f"✅ 프로그램 종료 완료")

# ================================================================================
# 🎯 메인 메뉴 시스템 (모드 선택)
# ================================================================================

async def main():
    """🎯 메인 메뉴 시스템"""
    print("🔥 스마트 자동 매수 스캘핑 시스템 V3.2")
    print("="*70)
    
    # 🕐 현재 시간 상태 표시
    server_time, can_trade = show_time_status()
    
    print(f"\n📋 실행 모드 선택:")
    print(f"1. 🧪 테스트 모드 (30초 간격, 시간 제약 없음)")
    print(f"2. 💰 실전 매매 모드 (60초 간격, 시간 제약 있음)")
    print(f"3. 🕐 시간 상태만 확인")
    print(f"0. 🚪 종료")
    
    try:
        choice = input(f"\n선택하세요 (0-3): ").strip()
        
        if choice == '0':
            print("👋 프로그램을 종료합니다.")
            return
        elif choice == '1':
            print("\n🧪 [테스트 모드] 선택됨")
            print("   • 루프 간격: 30초 (5초 간격 업데이트)")
            print("   • 시간 제약: 없음") 
            print("   • V2 NTP 시스템 사용")
            input("계속하려면 Enter를 누르세요...")
            await main_trading_loop(test_mode=True)
        elif choice == '2':
            print("\n💰 [실전 매매 모드] 선택됨")
            print("   • 루프 간격: 60초 (5초 간격 업데이트)")
            print("   • 시간 제약: 엄격 적용")
            print("   • V2 NTP 시스템 사용")
            
            if not can_trade:
                print("⚠️ 현재 매매 가능 시간이 아닙니다!")
                print("💡 테스트 모드(1번)를 선택하거나 매매 시간에 다시 실행해주세요.")
                return
            
            input("계속하려면 Enter를 누르세요...")
            await main_trading_loop(test_mode=False)
        elif choice == '3':
            print("\n✅ 시간 상태 확인 완료")
            return
        else:
            print("❌ 올바른 번호를 입력해주세요. (0-3)")
            await main()  # 다시 메뉴 표시
            
    except KeyboardInterrupt:
        print(f"\n👋 사용자가 프로그램을 종료했습니다.")
    except Exception as e:
        print(f"❌ 메뉴 실행 오류: {e}")
        import traceback
        traceback.print_exc()

# ================================================================================
# 프로그램 시작점
# ================================================================================

if __name__ == "__main__":
    try:
        # 초기 NTP 동기화
        print("🌐 V2 NTP 시스템 초기화 중...")
        sync_ntp_time(force=True)
        
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n👋 프로그램이 정상적으로 종료되었습니다.")
    except Exception as e:
        print(f"❌ 프로그램 실행 오류: {e}")
        import traceback
        traceback.print_exc()