"""
나만의 프롬프트 도서관 (Prompt Library)
----------------------------------------
프롬프트를 "도서"로, 카테고리를 "서가"로 비유한 콘솔 프로그램입니다.
필수 기능(추가/목록/카테고리별 조회/검색/상세보기/즐겨찾기) +
보너스 1(JSON 저장/불러오기, 카테고리별 Markdown 내보내기) +
보너스 2(수정/삭제 CRUD, 조회수 기록, TOP 목록)를 모두 포함합니다.
"""

import json
import os

CATEGORIES = ["텍스트 생성", "이미지 생성", "영상 생성", "페르소나", "자동화", "기타"]
DATA_FILE = "library_data.json"
EXPORT_DIR = "exports"

# 기본 프롬프트(도서) 데이터 - 이전 미션에서 작성한 프롬프트
books = [
    {
        "title": "거래처 팔로업 메일 작성 시스템 프롬프트",
        "content": (
            "당신은 B2B 소싱팀 사원 김민수입니다. 거래처에 서비스 영업 제안을 한 후 "
            "답변이 오지 않은 상황에서, 정중하고 친근한 팔로업 이메일 초안을 작성하는 것이 "
            "목표입니다.\n"
            "[출력 형식] 제목은 'OO 직함님, B2B 소싱팀 김민수입니다' 형식(직함 모르면 "
            "'담당자님'), 본문은 150~250자의 격식 있고 친근한 문체로 작성하고 연락처를 "
            "반드시 포함합니다.\n"
            "[금지 표현] '조속한 회신', '빠른 답변', '빠른 시일 내', '언제쯤', '확인 부탁' "
            "등 재촉하는 표현은 사용하지 않습니다.\n"
            "[안전장치] 거래처명, 담당자 직함, 제안 서비스명 중 하나라도 빠지면 메일을 "
            "먼저 작성하지 말고 최대 3개의 확인 질문을 먼저 합니다. 가격/계약 조건/납기일 "
            "등 입력에 없는 수치나 정책은 임의로 만들지 않고 '(확인 후 기재)'로 표시합니다."
        ),
        "category": "텍스트 생성",
        "favorite": True,
        "views": 0,
    },
    {
        "title": "IT 서비스 기획 전문가 Custom Instruction",
        "content": (
            "당신은 IT 서비스 기획 전문가(PM/PO)입니다. 사용자가 서비스 아이디어, 비즈니스 "
            "모델, 플랫폼, 앱, 웹 서비스 또는 AI 서비스 관련 아이디어를 입력하면 실무 서비스 "
            "기획 문서 형식으로 답변합니다.\n"
            "[답변 형식] 1) 서비스 개요(서비스명/한 줄 소개/타겟 사용자) 2) 문제 정의 "
            "3) 핵심 기능 4) 사용자 시나리오 5) 기대 효과 6) MVP 범위 7) 향후 확장 방안 "
            "순서로 작성합니다.\n"
            "[작성 원칙] 표 형식을 적극 활용하고, 핵심 내용을 먼저 제시하며, 모호한 표현 "
            "대신 구체적인 예시를 듭니다. MVP와 확장 기능을 명확히 구분하고, 답변 마지막에는 "
            "항상 '기획자 관점 추가 제안' 섹션을 포함합니다. 모든 답변은 한국어로 작성합니다."
        ),
        "category": "페르소나",
        "favorite": False,
        "views": 0,
    },
    {
        "title": "PetCare+ 서비스 인포그래픽 생성 프롬프트",
        "content": (
            "PetCare+를 위한 전문적인 SaaS 플랫폼 인포그래픽을 제작해 주세요.\n"
            "포함 요소: 반려동물 건강 프로필 관리, 예방접종 관리, AI 건강 분석, 운동 및 "
            "활동량 추적, 수의사 상담, 펫 보험 연계.\n"
            "디자인 스타일: 현대적인 스타트업 스타일 인포그래픽, 블루와 그린 계열 컬러, "
            "깔끔하고 직관적인 UI 디자인, 디지털 헬스케어 및 테크 플랫폼 분위기, 데이터 "
            "흐름과 서비스 구조가 한눈에 보이도록 시각화, 신뢰감 있고 미래지향적인 느낌 "
            "강조, 16:9 비율의 고해상도, 투자자 발표 및 사업계획서에 삽입 가능한 품질."
        ),
        "category": "이미지 생성",
        "favorite": False,
        "views": 0,
    },
    {
        "title": "FIT FIT 브랜드 광고 - 인물 등장 씬 프롬프트",
        "content": (
            "hooded figure standing in rainy cyberpunk street, center frame, holographic "
            "iridescent jacket, neon reflections, facing camera with face obscured by hood "
            "shadow, cinematic, shallow DOF, --ar 16:9\n"
            "[연출 의도] 사이버펑크 도시 브랜드 광고(FIT FIT)의 씬 2. 얼굴을 후드 음영으로 "
            "가려 신비감을 유지하면서 홀로그래픽 재킷의 질감과 네온 반사를 강조하는 것이 "
            "목표. Midjourney v6로 이미지를 생성한 뒤 Google Flow(Veo 3)로 슬로우 줌인 "
            "모션을 적용한다."
        ),
        "category": "영상 생성",
        "favorite": False,
        "views": 0,
    },
]


def show_menu():
    print("\n=== 나만의 프롬프트 도서관 ===")
    print("1. 신간 등록 (프롬프트 추가)")
    print("2. 전체 서가 보기 (목록)")
    print("3. 분야별 서가 (카테고리별 조회)")
    print("4. 도서 검색")
    print("5. 도서 상세 열람")
    print("6. 추천 도서 등록/해제 (즐겨찾기)")
    print("7. 추천 도서 서가 (즐겨찾기 목록)")
    print("8. 도서 정보 수정")
    print("9. 도서 폐기 (삭제)")
    print("10. 인기 도서 TOP 목록 (조회수 순)")
    print("11. 도서관 저장하기 (JSON)")
    print("12. 도서관 불러오기 (JSON)")
    print("13. 서가별 내보내기 (Markdown)")
    print("0. 도서관 문 닫기 (종료)")
    return input("선택: ").strip()

def choose_category():
    print("\n분야(서가) 선택:")
    for idx, cat in enumerate(CATEGORIES, start=1):
        print(f"{idx}) {cat}")
    print(f"{len(CATEGORIES) + 1}) 직접 입력")
    choice = input("선택: ").strip()
    if choice.isdigit():
        num = int(choice)
        if 1 <= num <= len(CATEGORIES):
            return CATEGORIES[num - 1]
        if num == len(CATEGORIES) + 1:
            custom = input("카테고리 직접 입력: ").strip()
            return custom if custom else "기타"
    print("잘못된 선택입니다. '기타'로 등록합니다.")
    return "기타"

def add_prompt():
    print("\n=== 신간 등록 (프롬프트 추가) ===")
    title = input("제목: ").strip()
    while not title:
        title = input("제목을 입력해야 합니다. 다시 입력: ").strip()
 
    content = input("내용: ").strip()
    while not content:
        content = input("내용을 입력해야 합니다. 다시 입력: ").strip()
 
    category = choose_category()
 
    books.append(
        {
            "title": title,
            "content": content,
            "category": category,
            "favorite": False,
            "views": 0,
        }
    )
    print(f"\n'{title}' 도서가 서가에 등록되었습니다!")
    
def show_list():
    print("\n=== 전체 서가 보기 ===")
    if not books:
        print("서가에 등록된 도서가 없습니다.")
        return
    for i, b in enumerate(books, start=1):
        star = " ⭐" if b["favorite"] else ""
        print(f"{i}. [{b['category']}] {b['title']}{star}")
    print(f"\n총 {len(books)}개의 프롬프트(도서)")
    
def show_by_category():
    print("\n=== 분야별 서가 조회 ===")
    for idx, cat in enumerate(CATEGORIES, start=1):
        print(f"{idx}) {cat}")
    choice = input("선택: ").strip()
    if not choice.isdigit() or not (1 <= int(choice) <= len(CATEGORIES)):
        print("잘못된 선택입니다.")
        return
    category = CATEGORIES[int(choice) - 1]
    result = [b for b in books if b["category"] == category]
    print(f"\n[{category}] 서가:")
    if not result:
        print("이 서가에는 등록된 도서가 없습니다.")
        return
    for i, b in enumerate(result, start=1):
        star = " ⭐" if b["favorite"] else ""
        print(f"{i}. {b['title']}{star}")
    print(f"\n총 {len(result)}개의 프롬프트(도서)")
    
def search_prompt():
    print("\n=== 도서 검색 ===")
    keyword = input("검색어: ").strip()
    if not keyword:
        print("검색어를 입력해야 합니다.")
        return
    result = [b for b in books if keyword in b["title"] or keyword in b["content"]]
    print("\n검색 결과:")
    if not result:
        print("검색 결과가 없습니다.")
        return
    for i, b in enumerate(result, start=1):
        star = " ⭐" if b["favorite"] else ""
        print(f"{i}. [{b['category']}] {b['title']}{star}")
    print(f"\n{len(result)}개의 프롬프트를 찾았습니다.")    

def show_detail():
    print("\n=== 도서 상세 열람 ===")
    show_list()
    if not books:
        return
    num = input("번호 입력: ").strip()
    if not num.isdigit() or not (1 <= int(num) <= len(books)):
        print("잘못된 번호입니다.")
        return
    b = books[int(num) - 1]
    b["views"] += 1
    star = "⭐" if b["favorite"] else "없음"
    print("\n" + "─" * 30)
    print(f"제목: {b['title']}")
    print(f"카테고리: {b['category']}")
    print(f"즐겨찾기: {star}")
    print(f"조회수: {b['views']}회")
    print("─" * 30)
    print("내용:")
    print(b["content"])
    print("─" * 30)
 
 
def toggle_favorite():
    print("\n=== 추천 도서 등록/해제 ===")
    show_list()
    if not books:
        return
    num = input("프롬프트 번호 입력: ").strip()
    if not num.isdigit() or not (1 <= int(num) <= len(books)):
        print("잘못된 번호입니다.")
        return
    b = books[int(num) - 1]
    b["favorite"] = not b["favorite"]
    status = "추가" if b["favorite"] else "해제"
    print(f"'{b['title']}' 프롬프트를 즐겨찾기에서 {status}했습니다!")

def show_favorites():
    print("\n=== 추천 도서 서가 (즐겨찾기 목록) ===")
    result = [b for b in books if b["favorite"]]
    if not result:
        print("즐겨찾기한 도서가 없습니다.")
        return
    for i, b in enumerate(result, start=1):
        print(f"{i}. [{b['category']}] {b['title']} ⭐")
    print(f"\n총 {len(result)}개의 즐겨찾기")
 
def edit_prompt():
    print("\n=== 도서 정보 수정 ===")
    show_list()
    if not books:
        return
    num = input("수정할 번호 입력: ").strip()
    if not num.isdigit() or not (1 <= int(num) <= len(books)):
        print("잘못된 번호입니다.")
        return
    b = books[int(num) - 1]
    print("변경하지 않으려면 그냥 엔터를 누르세요.")
    new_title = input(f"제목 ({b['title']}): ").strip()
    new_content = input("내용 (엔터 시 유지): ").strip()
    if new_title:
        b["title"] = new_title
    if new_content:
        b["content"] = new_content
    if input("카테고리를 다시 선택하시겠습니까? (y/n): ").strip().lower() == "y":
        b["category"] = choose_category()
    print("도서 정보가 수정되었습니다!")
 
 
def delete_prompt():
    print("\n=== 도서 폐기 (삭제) ===")
    show_list()
    if not books:
        return
    num = input("삭제할 번호 입력: ").strip()
    if not num.isdigit() or not (1 <= int(num) <= len(books)):
        print("잘못된 번호입니다.")
        return
    removed = books.pop(int(num) - 1)
    print(f"'{removed['title']}' 도서를 폐기했습니다.")

def show_top_viewed():
    print("\n=== 인기 도서 TOP 목록 ===")
    if not books:
        print("등록된 도서가 없습니다.")
        return
    ranked = sorted(books, key=lambda b: b["views"], reverse=True)
    for i, b in enumerate(ranked[:5], start=1):
        star = " ⭐" if b["favorite"] else ""
        print(f"{i}. [{b['category']}] {b['title']} - 조회수 {b['views']}회{star}")
 
def save_to_json():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(books, f, ensure_ascii=False, indent=2)
        print(f"\n'{DATA_FILE}' 파일로 도서관을 저장했습니다!")
    except OSError as e:
        print(f"저장 중 오류가 발생했습니다: {e}")
 
 
def load_from_json():
    global books
    if not os.path.exists(DATA_FILE):
        print(f"\n'{DATA_FILE}' 파일이 없습니다. 먼저 저장해주세요.")
        return
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            books = json.load(f)
        print(f"\n'{DATA_FILE}' 파일에서 도서관을 불러왔습니다!")
    except (OSError, json.JSONDecodeError) as e:
        print(f"불러오기 중 오류가 발생했습니다: {e}")

def main():
    while True:
        choice = show_menu()
        if choice == "1":
            add_prompt()
        elif choice == "2":
            show_list()
        elif choice == "3":
            show_by_category()
        elif choice == "4":
            search_prompt()
        elif choice == "5":
            show_detail()
        elif choice == "6":
            toggle_favorite()
        elif choice == "7":
            show_favorites()
        elif choice == "8":
            edit_prompt()
        elif choice == "9":
            delete_prompt()
        elif choice == "10":
            show_top_viewed()
        elif choice == "11":
            save_to_json()
        elif choice == "12":
            load_from_json()
        elif choice == "13":
            export_markdown_by_category()
        elif choice == "0":
            print("\n도서관 문을 닫습니다. 이용해주셔서 감사합니다!")
            break
        else:
            print("\n잘못된 번호입니다. 다시 선택해주세요.")

if __name__ == "__main__":
    pass