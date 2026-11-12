# Sky Striker 봇

Python 3과 Playwright를 사용합니다.

```sh
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium
python3 state_bot.py --login --headless
```

닉네임과 PIN은 실행 시 입력합니다. PIN은 저장하지 않습니다. macOS에서 화면을 보려면 `python3 state_bot.py --login`을 실행하세요. Linux에서 창을 띄우려면 그래픽 디스플레이가 필요합니다. `--browser chrome`과 `--browser chromium`으로 브라우저를 선택할 수 있습니다.

기본 실행에는 시간 제한이 없습니다. 게임 오버 또는 올클리어까지 진행합니다. 시험용 시간 제한은 `--seconds`로 명시할 때만 적용됩니다.

## 보통부터 어려움까지 실행 후 macOS 잠자기

```sh
caffeinate -i python3 state_bot.py --login --campaign --sleep-when-done
```

보통 실패 시 결과 화면을 유지하고 잠자기로 전환합니다. 보통 올클리어 시 같은 브라우저에서 어려움을 새로 시작하고, 어려움의 게임 오버 또는 올클리어 이후 잠자기로 전환합니다. 두 난이도 모두 시간 제한이 없습니다. 서버의 랭킹 제출 응답을 확인한 후 전환합니다. 실행 오류 시 자동으로 잠자기에 들지 않습니다.

## 휴대폰 진행 상태

```sh
python3 monitor.py
```

같은 Wi-Fi의 휴대폰에서 `http://맥북의LAN주소:8765`에 접속하면 스테이지, 점수, 체력, 장비를 확인할 수 있습니다. 이 서버는 공개된 게임 진행 정보만 제공합니다. 일반 파일 디렉터리를 노출하지 않습니다. 인터넷 외부에서는 직접 접근할 수 없으며, 별도 VPN 또는 화면 공유가 필요합니다. 봇은 2초마다 `status.json`을 갱신합니다. Mac이 잠들면 갱신과 접속이 중단됩니다.

게임 주소에 클라우드에서 접속할 수 있어야 플레이가 가능합니다. 연결 가능 여부는 실행 환경에 따라 다릅니다. 봇은 브라우저에서 게임 상태를 읽고 키보드로 조작합니다. 실행마다 별도 프로필로 시작하며, `--resume` 옵션은 게임 서버의 이어하기 기록을 사용합니다.
