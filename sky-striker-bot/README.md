# Sky Striker 봇

Python 3과 Playwright를 사용해 게임을 플레이합니다.

```sh
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium
python3 state_bot.py --login --headless
```

닉네임과 PIN은 실행 시 입력합니다. 저장소나 명령행 인자에 적지 마세요. macOS에서 화면을 보려면 `python3 state_bot.py --login`을 실행하세요. Linux에서 창을 띄우려면 그래픽 디스플레이가 필요합니다. `--browser chrome`과 `--browser chromium`으로 브라우저를 선택할 수 있습니다.

게임 주소는 Tailscale 도메인입니다. 클라우드 환경에서 해당 주소에 접근할 수 있어야 로그인과 플레이가 가능합니다. 연결 가능 여부는 실행 환경에 따라 다릅니다. 봇은 플레이하는 브라우저의 게임 상태를 읽고 키보드로 조작합니다. 실행이 끝나면 랭킹 제출 결과를 출력합니다.
