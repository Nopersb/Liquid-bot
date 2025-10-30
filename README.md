# Hyperliquid BTC Short Trading Bot

⚠️ **경고: 이 봇은 극도로 위험합니다!**

수수료와 슬리피지로 인한 손실이 누적됩니다. 테스트 목적이 아니라면 실제 자금으로 사용하지 마세요.

## 개요

Hyperliquid에서 BTC 숏 포지션을 반복적으로 열고 닫는 자동 거래 봇입니다.

## 주요 기능

- 🔄 자동 숏 포지션 진입 및 청산
- 📊 실시간 포지션 모니터링
- ⏱️ 랜덤 대기 시간 (5~10분)
- 💰 손익 추적

## 설치 방법

1. 저장소 클론:
```bash
git clone [your-repo-url]
cd [repo-name]
```

2. 필요한 패키지 설치:
```bash
pip install eth-account hyperliquid-python-sdk python-dotenv requests
```

3. 환경변수 설정:
```bash
cp .env.example .env
# .env 파일을 편집하여 실제 개인키 입력
```

## 사용 방법

```bash
python liquid.py
```

## 설정

`liquid.py` 파일에서 다음 설정을 변경할 수 있습니다:

- `TRADE_SIZE`: 거래 크기 (기본값: 0.01 BTC)
- `WAIT_MIN`: 최소 대기 시간 (기본값: 300초)
- `WAIT_MAX`: 최대 대기 시간 (기본값: 600초)
- `MAX_WAIT_FOR_FILL`: 체결 대기 시간 (기본값: 30초)

## 주의사항

⚠️ **이 봇은 교육 목적으로만 사용하세요**

- 실제 거래에서는 수수료와 슬리피지로 인해 지속적인 손실이 발생할 가능성이 높습니다
- 테스트 환경에서 충분히 테스트한 후 사용하세요
- 투자 손실에 대한 책임은 사용자에게 있습니다

## 라이선스

MIT License

## 면책조항

이 소프트웨어는 "있는 그대로" 제공되며, 어떠한 보증도 하지 않습니다. 사용으로 인한 모든 손실은 사용자의 책임입니다.
