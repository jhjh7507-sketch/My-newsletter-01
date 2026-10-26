# 수업 녹음 → 카톡 정리 자동화

트레이너가 수업을 녹음하면 아이폰 단축어가 드라이브에 올린다. 예약 작업이 아래 두 모드로 돈다.
정리 규칙은 `.claude/pt/kakao-style.md`. 이 작업 중에는 git 커밋·푸시를 하지 않는다.

## 드라이브
| 폴더 | ID | 내용 |
|---|---|---|
| 수업녹음 | `126Sol0WoFopiFiDpnS_41K-VfVh_2eXH` | 녹음 m4a. 파일 이름 = 업로드 시각(KST) `yyyy-MM-dd HH-mm.m4a` |
| 카톡정리 | `1-Gxj2AWmHLqGnUty-_D0DhxMvRYetYOT` | 보낼 글. 제목 `YYYY-MM-DD 이름 회원님` |
| 회원기록 | `1o4uTHlS1jEVWOJEplkG5XHe9oHJGtSfG` | 회원별 수업 기록. 제목 `이름 YYYY-MM-DD 기록` |

## 모드 A: 하루 계획 (매일 아침)
1. 구글 캘린더에서 오늘(KST) 일정 중 제목에 "회원님"이 들어간 것을 모두 찾는다
   (`list_events` 오늘 00:00~24:00, `fullText` "회원님". 할당량 오류가 나면 `search_events` "회원님"으로 찾아 오늘 것만 고른다).
   제목 "최윤정회원님" → 이름 "최윤정".
2. 이미 있는 예약 작업 목록(`list_triggers`)을 본다. 이름이 `수업정리 <이름> <MM/DD HH:MM>`인 것이 이미 있으면 건너뛴다.
3. 남은 수업마다 `create_trigger`로 한 번만 도는 예약 작업을 만든다.
   - name: `수업정리 <이름> <MM/DD HH:MM>` (HH:MM = 수업 시작)
   - run_once_at: 수업 끝 + 10분 (UTC로 변환한 RFC3339). 이미 지난 수업은 건너뛴다.
   - create_new_session_on_fire: true, notifications: {"push": true}
   - connectors: ["Google Drive", "Google Calendar"], initiation: human_schedule
   - prompt: `모드 B. 회원: <이름>, 수업: <YYYY-MM-DD> <HH:MM>-<HH:MM> KST, 시도: 1.` + 아래 "공통 시작"
4. 만든 목록을 한 줄씩 출력하고 끝낸다.

## 모드 B: 수업 하나 정리
1. 카톡정리 폴더에 `YYYY-MM-DD 이름 회원님`이 이미 있으면 그 내용을 출력하고 끝낸다.
2. 수업녹음 폴더에서 `createdTime`이 (수업 시작 - 10분) ~ (수업 끝 + 20분)인 파일을 찾는다 (`parentId = '<수업녹음 ID>'`).
   - 없으면: 시도가 1이나 2면 같은 prompt에 시도+1로 20분 뒤 한 번 도는 예약 작업을 만들고
     "녹음이 아직 안 올라왔어요. 20분 뒤 다시 확인할게요"라고 출력하고 끝낸다. 시도 3이면
     "<이름> 회원님 수업 녹음을 못 찾았어요. 올리시면 '드라이브 확인해줘'라고 말씀해 주세요"라고 출력하고 끝낸다.
3. 파일을 `createdTime` 순으로 `download_file_content`로 받는다. 결과가 커서 파일로 저장되면 그 JSON의
   `content`(base64)를 디코드해 스크래치패드에 `.m4a`로 쓴다.
4. `python3 .claude/pt/stt.py <스크래치패드>/class <파일들...>` 로 글로 바꾸고 결과 txt를 전부 읽는다.
5. 맥락을 모은다.
   - 회원기록 폴더에서 제목에 이름이 들어간 기록 중 최근 2개를 읽는다 (지난 무게·이슈와 비교할 거리).
   - 캘린더에서 이 회원의 다음 수업 날짜를 찾는다 (`search_events` 이름).
6. `kakao-style.md` 규칙대로 카톡 글을 쓴다. 녹음 속 이름이 음성인식으로 틀려도 캘린더 이름을 쓴다.
   운동 이름·무게가 녹음에서 확실치 않으면 그 자리를 `[확인: ...]`으로 남긴다.
7. 저장한다.
   - 카톡정리 폴더: 제목 `YYYY-MM-DD 이름 회원님`, 내용 = 카톡 글 (text/plain).
   - 회원기록 폴더: 제목 `이름 YYYY-MM-DD 기록`, 내용 = 루틴(운동·무게·개수·세트)과 다음 수업 비교용 메모
     (통증, 컨디션, 고친 자세, 무게 이야기).
8. 마지막 응답은 카톡 글 그대로만 출력한다 (앞뒤 설명 없이, `[확인: ...]`이 있으면 맨 끝에 한 줄로 알린다).

## 공통 시작 (예약 작업 prompt 끝에 붙인다)
`git fetch origin claude/update-agent-index-config-pg0055 && git checkout FETCH_HEAD -- .claude/pt` 로 규칙 파일을 받은 뒤
`.claude/pt/run.md`를 읽고 해당 모드대로 진행.
