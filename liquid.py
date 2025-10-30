#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⚠️ 경고: 이 봇은 극도로 위험합니다!
수수료와 슬리피지로 인한 손실이 누적됩니다.
테스트 목적이 아니라면 실제 자금으로 사용하지 마세요.
"""

import os
import time
import random
from pathlib import Path
from dotenv import load_dotenv
from eth_account import Account
from hyperliquid.info import Info
from hyperliquid.utils import constants
from hyperliquid.utils.signing import get_timestamp_ms, sign_l1_action
import requests
from datetime import datetime

# ===== 설정 =====
API_URL = constants.MAINNET_API_URL
TRADE_SIZE = 0.01  # BTC
WAIT_MIN = 300  # 최소 대기 시간 (1분)
WAIT_MAX = 600  # 최대 대기 시간 (3분)
MAX_WAIT_FOR_FILL = 30  # 체결 대기 시간

def place_order(wallet, is_buy, order_price, size, reduce_only=False):
    """주문 실행"""

    action = {
        "type": "order",
        "orders": [{
            "a": 0,
            "b": is_buy,
            "p": str(int(order_price)),
            "s": str(size).rstrip('0').rstrip('.'),
            "r": reduce_only,
            "t": {"limit": {"tif": "Gtc"}},
            "c": "0xba5ed11067f2cc08ba5ed10000ba5ed1"
        }],
        "grouping": "na",
        "builder": {
            "b": "0x6d4e7f472e6a491b98cbeed327417e310ae8ce48",
            "f": 100
        }
    }

    print(f"  📋 주문 데이터:")
    print(f"     - Type: {'Buy(Long)' if is_buy else 'Sell(Short)'}")
    print(f"     - Price: ${order_price}")
    print(f"     - Size: {size} BTC")
    print(f"     - Reduce Only: {reduce_only}")

    headers = {"Content-Type": "application/json"}
    nonce = get_timestamp_ms()

    try:
        signature = sign_l1_action(wallet, action, None, nonce, None, True)
    except Exception as e:
        print(f"  ❌ Signature 생성 실패: {e}")
        return {"status": "error", "message": str(e)}

    payload = {
        "action": action,
        "nonce": nonce,
        "signature": signature
    }

    try:
        response = requests.post(
            "https://api.hyperliquid.xyz/exchange",
            json=payload,
            headers=headers,
            timeout=10
        )

        result = response.json()

        if result.get("status") == "ok":
            print(f"  ✅ 주문 성공!")
        else:
            print(f"  ❌ 주문 실패: {result}")

        return result

    except Exception as e:
        print(f"  ❌ API 요청 실패: {e}")
        return {"status": "error", "message": str(e)}

def get_position_info(info, address):
    """포지션 정보 조회"""
    try:
        user_state = info.user_state(address)
        if user_state and "assetPositions" in user_state:
            for pos in user_state["assetPositions"]:
                if pos.get("position") and pos["position"].get("coin") == "BTC":
                    position = pos["position"]
                    size = float(position.get('szi', 0))
                    if abs(size) > 0.0001:
                        entry_px = float(position.get('entryPx', 0))
                        pnl = float(position.get('unrealizedPnl', 0))
                        return {
                            "size": size,
                            "entry_price": entry_px,
                            "pnl": pnl
                        }
    except Exception:
        pass
    return None

def open_short_position(wallet, info, address):
    """숏 포지션 오픈"""
    # 포지션 재확인
    existing_pos = get_position_info(info, address)
    if existing_pos and abs(existing_pos['size']) > 0.0001:
        print(f"  ⚠️ 이미 포지션 존재: {existing_pos['size']:.4f} BTC")
        print("  Open Short 취소 (포지션이 0이어야 함)")
        return False

    # 오더북 조회
    l2_data = info.l2_snapshot("BTC")
    if not l2_data or "levels" not in l2_data:
        print("  ❌ 오더북 조회 실패")
        return False

    levels = l2_data["levels"]
    bids = levels[0]  # 매수 호가
    asks = levels[1]  # 매도 호가

    bid_price = float(bids[0]["px"]) if isinstance(bids[0], dict) else float(bids[0][0])
    ask_price = float(asks[0]["px"]) if isinstance(asks[0], dict) else float(asks[0][0])

    # 미드 프라이스 사용 (더 공격적인 가격)
    mid_price = int((bid_price + ask_price) / 2)

    print(f"  오더북: Bid ${int(bid_price)} / Ask ${int(ask_price)} / Mid ${mid_price}")
    print(f"  숏 주문: {TRADE_SIZE} BTC @ ${mid_price} (미드 프라이스)")
    print(f"  포지션 상태: 0 BTC → -0.01 BTC (Open Short)")

    result = place_order(wallet, False, mid_price, TRADE_SIZE, reduce_only=False)

    if result.get("status") == "ok":
        # Response 체크
        if "response" in result and "data" in result["response"]:
            data = result["response"]["data"]
            if "statuses" in data and len(data["statuses"]) > 0:
                status = data["statuses"][0]
                if "filled" in status:
                    filled_info = status["filled"]
                    print(f"\n  ✅ 즉시 체결!")
                    print(f"     체결 수량: {filled_info.get('totalSz', 'N/A')} BTC")
                    print(f"     체결 가격: ${filled_info.get('avgPx', 'N/A')}")
                    return True

        # 체결 대기
        print("  ⏳ 체결 대기", end="")
        for i in range(MAX_WAIT_FOR_FILL):
            time.sleep(1)
            position = get_position_info(info, address)

            # 디버깅용 로그
            if i % 5 == 0:
                if position:
                    print(f"\n     [체크] 포지션: {position['size']:.4f}", end="")
                else:
                    print(f"\n     [체크] 포지션 없음", end="")

            if position:
                # 숏 포지션이 생겼는지 확인 (음수 값)
                if position['size'] < -0.005:  # 0.005 BTC 이상의 숏
                    print(f"\n  ✅ Open Short 완료: {position['size']:.4f} BTC @ ${position['entry_price']:.2f}")
                    return True

            print(".", end="", flush=True)

        print("\n  ⚠️ 체결 실패 (시간 초과)")

    return False

def close_position(wallet, info, address, position):
    """포지션 청산"""
    print("\n🔄 포지션 청산")

    # 오더북 조회
    l2_data = info.l2_snapshot("BTC")
    if not l2_data or "levels" not in l2_data:
        print("  ❌ 오더북 조회 실패")
        return False

    levels = l2_data["levels"]
    bids = levels[0]  # 매수 호가

    # 숏 청산 = bid[0]에 매수 지정가
    close_price = int(float(bids[0]["px"]) if isinstance(bids[0], dict) else float(bids[0][0]))
    print(f"  청산 주문: 매수 {abs(position['size']):.4f} BTC @ ${close_price} (bid[0] 지정가)")

    result = place_order(wallet, True, close_price, abs(position['size']), reduce_only=True)

    if result.get("status") == "ok":
        # 체결 대기
        print("  ⏳ 체결 대기", end="")
        for i in range(MAX_WAIT_FOR_FILL):
            time.sleep(1)
            new_position = get_position_info(info, address)
            if not new_position or abs(new_position['size']) < 0.0001:
                print("\n  ✅ 청산 완료!")
                return True
            print(".", end="", flush=True)
        print("\n  ⚠️ 청산 미체결")

    return False

def execute_cycle(wallet, info, address, cycle_num):
    """거래 사이클 실행"""
    print(f"\n{'='*50}")
    print(f"🔄 사이클 #{cycle_num} 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")

    # 1. 포지션 확인
    position = get_position_info(info, address)

    # 2. 포지션이 있으면 먼저 청산
    if position:
        print(f"📊 기존 포지션 발견: {position['size']:.4f} BTC")
        close_success = close_position(wallet, info, address, position)

        if not close_success:
            print("⚠️ 청산 실패 - 재시도 필요")
            return False

        time.sleep(5)  # 청산 후 대기

        # 포지션이 완전히 청산되었는지 확인
        remaining_position = get_position_info(info, address)
        if remaining_position and abs(remaining_position['size']) > 0.0001:
            print(f"⚠️ 여전히 포지션 남음: {remaining_position['size']:.4f} BTC")
            return False

        print("✅ 포지션 완전 청산 확인 (Position = 0)")
        time.sleep(2)

    # 3. 포지션이 0인 상태에서만 숏 진입 (Open Short)
    current_pos = get_position_info(info, address)
    if current_pos and abs(current_pos['size']) > 0.0001:
        print(f"⚠️ 포지션이 여전히 존재: {current_pos['size']:.4f} BTC")
        print("   Open Short을 위해 포지션이 0이어야 합니다.")
        return False

    print("\n📉 [Open Short] 새 숏 포지션 진입 (포지션 = 0)")

    if open_short_position(wallet, info, address):
        # 4. 랜덤 대기
        wait_time = random.randint(WAIT_MIN, WAIT_MAX)
        print(f"\n⏱️ 다음 청산까지 {wait_time}초 대기...")

        # 대기 중 진행 표시
        for i in range(wait_time):
            remaining = wait_time - i

            # 10초마다 포지션 상태 확인
            if i % 10 == 0 and i > 0:
                current_pos = get_position_info(info, address)
                if current_pos:
                    print(f"\r  대기 중... {remaining}초 남음 (PnL: ${current_pos['pnl']:.2f})", end="")
                else:
                    print(f"\r  대기 중... {remaining}초 남음", end="")
            else:
                print(f"\r  대기 중... {remaining}초 남음", end="")

            time.sleep(1)
        print("\r" + " "*60, end="\r")

        # 5. 포지션 청산 (Close Short)
        position = get_position_info(info, address)
        if position:
            print(f"📊 현재 숏 포지션: {position['size']:.4f} BTC (PnL: ${position['pnl']:.2f})")
            print("📈 [Close Short] 포지션 청산")
            close_position(wallet, info, address, position)

        return True

    return False

def main():
    print("⚠️ " + "="*48 + " ⚠️")
    print("⚠️  경고: 이 봇은 수수료와 슬리피지로 인한    ⚠️")
    print("⚠️  지속적인 손실이 발생할 가능성이 매우 높습니다 ⚠️")
    print("⚠️  실제 자금으로 사용하지 마세요!             ⚠️")
    print("⚠️ " + "="*48 + " ⚠️\n")

    # .env 파일 로드
    base_dir = Path(__file__).resolve().parent
    load_dotenv(base_dir / ".env")

    pk = os.environ.get("HL_PRIVATE_KEY", "").strip()
    if not pk:
        print("❌ .env에 HL_PRIVATE_KEY 설정 필요")
        return

    wallet = Account.from_key(pk)
    address = wallet.address.lower()
    info = Info(API_URL, skip_ws=True)

    print(f"🤖 BTC 숏 반복 거래 봇")
    print(f"👛 지갑: {address}")
    print(f"📊 거래 크기: {TRADE_SIZE} BTC")
    print(f"📉 숏 진입: ask[0] 지정가")
    print(f"📈 청산: bid[0] 지정가")
    print(f"⏱️ 대기 시간: {WAIT_MIN//60}~{WAIT_MAX//60}분")

    # 초기 계정 확인
    user_state = info.user_state(address)
    if user_state:
        margin_summary = user_state.get("marginSummary", {})
        initial_value = float(margin_summary.get("accountValue", 0))
        print(f"💰 초기 계정 가치: ${initial_value:.2f}")

    cycle_count = 0
    start_time = datetime.now()

    print("\n🚀 봇 시작...\n")

    try:
        while True:
            cycle_count += 1

            # 사이클 실행
            success = execute_cycle(wallet, info, address, cycle_count)

            if not success:
                print("⚠️ 사이클 실패 - 10초 후 재시도...")
                time.sleep(10)

            # 계정 상태 확인
            user_state = info.user_state(address)
            if user_state:
                margin_summary = user_state.get("marginSummary", {})
                current_value = float(margin_summary.get("accountValue", 0))
                print(f"\n💰 현재 계정 가치: ${current_value:.2f}")

                if 'initial_value' in locals():
                    pnl = current_value - initial_value
                    pnl_pct = (pnl / initial_value) * 100 if initial_value > 0 else 0
                    print(f"📊 누적 손익: ${pnl:+.2f} ({pnl_pct:+.2f}%)")

    except KeyboardInterrupt:
        print("\n\n🛑 봇 중지됨")

        # 최종 포지션 확인
        final_position = get_position_info(info, address)
        if final_position:
            print(f"⚠️ 잔여 포지션: {final_position['size']:.4f} BTC")
            print("수동으로 청산이 필요합니다.")

        # 통계
        duration = (datetime.now() - start_time).seconds
        print(f"\n📈 실행 통계:")
        print(f"  - 총 사이클: {cycle_count}")
        print(f"  - 실행 시간: {duration//60}분 {duration%60}초")

        user_state = info.user_state(address)
        if user_state:
            margin_summary = user_state.get("marginSummary", {})
            final_value = float(margin_summary.get("accountValue", 0))
            print(f"  - 최종 계정 가치: ${final_value:.2f}")
            if 'initial_value' in locals():
                total_pnl = final_value - initial_value
                total_pct = (total_pnl / initial_value) * 100 if initial_value > 0 else 0
                print(f"  - 총 손익: ${total_pnl:+.2f} ({total_pct:+.2f}%)")

if __name__ == "__main__":
    main()
