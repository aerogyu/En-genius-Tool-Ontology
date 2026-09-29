# offline/ — 반입 패키지 자리

- 사내: 반입 패키지의 `wheels_win_amd64_cp310.zip` 을 **풀지 말고 이 폴더에 그대로** 둔다. `scripts\setup_offline.bat` 이 `offline\wheels\` 로 푼다.
- 개발 PC: `offline/wheels/`(wheel 수집)·`offline/package_<날짜>/`(패키지 조립)·`*.zip` 은 git 밖이다 (`.gitignore`).
- 패키지 받는 곳·구성·검증 기록: `README_offline.md` 1장, `docs/04_반입목록.md` 6장.
