# -*- coding: utf-8 -*-
"""
나만의 프롬프트 관리 프로그램
--------------------------------
GenAI 활용을 위해 쌓아온 프롬프트들을 카테고리별로 정리하고,
검색/즐겨찾기/조회수 관리까지 할 수 있는 콘솔 프로그램입니다.

실행 방법:
    python prompt_manager.py
"""

import json
import os

# ------------------------------------------------------------
# 상수 정의
# ------------------------------------------------------------
CATEGORIES = ["텍스트 생성", "이미지 생성", "영상 생성", "페르소나", "자동화", "기타"]
JSON_FILE = "prompts.json"
EXPORT_DIR = "exports"


# ------------------------------------------------------------
# 기본 데이터 (이전 미션에서 작성한 프롬프트 최소 3개 이상 등록)
# ------------------------------------------------------------
def create_default_prompts():
    """프로그램 시작 시 기본으로 등록되는 프롬프트 목록을 반환한다."""
    return [
        {
            "title": "블로그 글 작성 도우미",
            "content": (
                "당신은 10년 경력의 전문 블로거입니다. "
                "주어진 주제에 대해 SEO에 최적화된 블로그 글을 작성해주세요. "
                "서론, 본론, 결론 구조를 갖추고, 독자의 관심을 끄는 제목을 3개 제안해주세요."
            ),
            "category": "텍스트 생성",
            "favorite": True,
            "views": 0,
        },
        {
            "title": "제품 썸네일 생성",
            "content": (
                "다음 제품의 매력적인 썸네일 이미지를 생성해주세요. "
                "배경은 깔끔한 화이트 스튜디오 톤으로, 제품이 정중앙에 위치하도록 하고 "
                "자연광이 비치는 느낌으로 표현해주세요."
            ),
            "category": "이미지 생성",
            "favorite": False,
            "views": 0,
        },
        {
            "title": "IT 컨설턴트 페르소나",
            "content": (
                "당신은 15년 경력의 IT 전략 컨설턴트입니다. "
                "기술적인 내용을 비전문가도 이해할 수 있도록 쉽게 설명하며, "
                "항상 비즈니스 임팩트 관점에서 조언합니다."
            ),
            "category": "페르소나",
            "favorite": False,
            "views": 0,
        },
        {
            "title": "뉴스 요약 프롬프트",
            "content": (
                "다음 뉴스 기사를 3줄로 요약해주세요. "
                "핵심 사실, 배경, 전망을 각각 한 문장으로 정리해주세요."
            ),
            "category": "자동화",
            "favorite": False,
            "views": 0,
        },
    ]


# ------------------------------------------------------------
# 공통 입력 유틸리티
# ------------------------------------------------------------
def get_non_empty_input(label):
    """빈 값이 입력되면 다시 입력을 요청하는 입력 함수."""
    while True:
        value = input(label).strip()
        if value:
            return value
        print("빈 값은 입력할 수 없습니다. 다시 입력해주세요.\n")


def choose_category():
    """카테고리 목록을 보여주고 선택하게 한 뒤 선택된 카테고리 이름을 반환한다."""
    print("\n카테고리 선택:")
    for i, cat in enumerate(CATEGORIES, start=1):
        print(f"{i}) {cat}")
    print(f"{len(CATEGORIES) + 1}) 직접 입력")

    choice = input("선택: ").strip()
    if choice.isdigit():
        idx = int(choice)
        if 1 <= idx <= len(CATEGORIES):
            return CATEGORIES[idx - 1]
        if idx == len(CATEGORIES) + 1:
            return get_non_empty_input("카테고리 이름 직접 입력: ")

    print("잘못된 입력입니다. '기타'로 설정합니다.")
    return "기타"


def get_valid_index(prompts, label="번호 입력: "):
    """유효한 프롬프트 번호를 입력받는다. 잘못된 입력이면 None을 반환한다."""
    if not prompts:
        print("등록된 프롬프트가 없습니다.")
        return None

    raw = input(label).strip()
    if not raw.isdigit():
        print("숫자로 입력해주세요.")
        return None

    idx = int(raw) - 1
    if idx < 0 or idx >= len(prompts):
        print("존재하지 않는 번호입니다.")
        return None
    return idx


# ------------------------------------------------------------
# 메뉴 출력
# ------------------------------------------------------------
def show_menu():
    print("\n=== 나만의 프롬프트 관리 ===")
    print("1. 프롬프트 추가")
    print("2. 프롬프트 목록")
    print("3. 카테고리별 조회")
    print("4. 프롬프트 검색")
    print("5. 프롬프트 상세 보기")
    print("6. 즐겨찾기 추가/해제")
    print("7. 즐겨찾기 목록")
    print("8. 프롬프트 수정")
    print("9. 프롬프트 삭제")
    print("10. 조회수 Top 목록")
    print("11. JSON 파일로 저장")
    print("12. JSON 파일 불러오기")
    print("13. 카테고리별 Markdown 내보내기")
    print("0. 종료")


# ------------------------------------------------------------
# 1. 프롬프트 추가
# ------------------------------------------------------------
def add_prompt(prompts):
    print("\n=== 프롬프트 추가 ===")
    title = get_non_empty_input("제목: ")
    content = get_non_empty_input("내용: ")
    category = choose_category()

    prompts.append(
        {
            "title": title,
            "content": content,
            "category": category,
            "favorite": False,
            "views": 0,
        }
    )
    print("\n프롬프트가 추가되었습니다!")


# ------------------------------------------------------------
# 2. 프롬프트 목록
# ------------------------------------------------------------
def show_list(prompts):
    print("\n=== 프롬프트 목록 ===")
    if not prompts:
        print("등록된 프롬프트가 없습니다.")
        return

    for i, p in enumerate(prompts, start=1):
        star = " ⭐" if p["favorite"] else ""
        print(f"{i}. [{p['category']}] {p['title']}{star}")

    print(f"\n총 {len(prompts)}개의 프롬프트")


# ------------------------------------------------------------
# 3. 카테고리별 조회
# ------------------------------------------------------------
def show_by_category(prompts):
    print("\n=== 카테고리별 조회 ===")
    for i, cat in enumerate(CATEGORIES, start=1):
        print(f"{i}) {cat}")

    choice = input("선택: ").strip()
    if not choice.isdigit() or not (1 <= int(choice) <= len(CATEGORIES)):
        print("잘못된 입력입니다.")
        return

    category = CATEGORIES[int(choice) - 1]
    filtered = [p for p in prompts if p["category"] == category]

    print(f"\n[{category}] 카테고리 프롬프트:")
    if not filtered:
        print("해당 카테고리에 프롬프트가 없습니다.")
        return

    for i, p in enumerate(filtered, start=1):
        star = " ⭐" if p["favorite"] else ""
        print(f"{i}. {p['title']}{star}")

    print(f"\n총 {len(filtered)}개의 프롬프트")


# ------------------------------------------------------------
# 4. 프롬프트 검색
# ------------------------------------------------------------
def search_prompt(prompts):
    print("\n=== 프롬프트 검색 ===")
    keyword = get_non_empty_input("검색어: ")

    results = [
        p
        for p in prompts
        if keyword.lower() in p["title"].lower() or keyword.lower() in p["content"].lower()
    ]

    print("\n검색 결과:")
    if not results:
        print("검색 결과가 없습니다.")
        return

    for i, p in enumerate(results, start=1):
        star = " ⭐" if p["favorite"] else ""
        print(f"{i}. [{p['category']}] {p['title']}{star}")

    print(f"\n{len(results)}개의 프롬프트를 찾았습니다.")


# ------------------------------------------------------------
# 5. 프롬프트 상세 보기 (보너스: 조회수 기록)
# ------------------------------------------------------------
def show_detail(prompts):
    print("\n=== 프롬프트 상세 보기 ===")
    show_list(prompts)
    idx = get_valid_index(prompts)
    if idx is None:
        return

    p = prompts[idx]
    p["views"] += 1  # 조회수 증가 (보너스 과제)

    star = "⭐" if p["favorite"] else "없음"
    print("\n" + "─" * 30)
    print(f"제목: {p['title']}")
    print(f"카테고리: {p['category']}")
    print(f"즐겨찾기: {star}")
    print(f"조회수: {p['views']}")
    print("─" * 30)
    print("내용:")
    print(p["content"])
    print("─" * 30)


# ------------------------------------------------------------
# 6. 즐겨찾기 추가/해제
# ------------------------------------------------------------
def toggle_favorite(prompts):
    print("\n=== 즐겨찾기 관리 ===")
    show_list(prompts)
    idx = get_valid_index(prompts)
    if idx is None:
        return

    p = prompts[idx]
    p["favorite"] = not p["favorite"]

    if p["favorite"]:
        print(f"\n'{p['title']}' 프롬프트를 즐겨찾기에 추가했습니다!")
    else:
        print(f"\n'{p['title']}' 프롬프트를 즐겨찾기에서 해제했습니다.")


# ------------------------------------------------------------
# 7. 즐겨찾기 목록
# ------------------------------------------------------------
def show_favorites(prompts):
    print("\n=== 즐겨찾기 목록 ===")
    favorites = [p for p in prompts if p["favorite"]]

    if not favorites:
        print("즐겨찾기한 프롬프트가 없습니다.")
        return

    for i, p in enumerate(favorites, start=1):
        print(f"{i}. [{p['category']}] {p['title']} ⭐")

    print(f"\n총 {len(favorites)}개의 즐겨찾기")


# ------------------------------------------------------------
# 8. 프롬프트 수정 (보너스: CRUD)
# ------------------------------------------------------------
def edit_prompt(prompts):
    print("\n=== 프롬프트 수정 ===")
    show_list(prompts)
    idx = get_valid_index(prompts)
    if idx is None:
        return

    p = prompts[idx]
    print(f"\n수정할 항목을 입력하세요. (변경하지 않으려면 엔터)")

    new_title = input(f"제목 [{p['title']}]: ").strip()
    new_content = input(f"내용 [{p['content'][:20]}...]: ").strip()

    change_category = input("카테고리를 변경하시겠습니까? (y/n): ").strip().lower()

    if new_title:
        p["title"] = new_title
    if new_content:
        p["content"] = new_content
    if change_category == "y":
        p["category"] = choose_category()

    print("\n프롬프트가 수정되었습니다!")


# ------------------------------------------------------------
# 9. 프롬프트 삭제 (보너스: CRUD)
# ------------------------------------------------------------
def delete_prompt(prompts):
    print("\n=== 프롬프트 삭제 ===")
    show_list(prompts)
    idx = get_valid_index(prompts)
    if idx is None:
        return

    p = prompts.pop(idx)
    print(f"\n'{p['title']}' 프롬프트가 삭제되었습니다.")


# ------------------------------------------------------------
# 10. 조회수 Top 목록 (보너스: 사용 기록)
# ------------------------------------------------------------
def show_top_viewed(prompts):
    print("\n=== 조회수 Top 목록 ===")
    if not prompts:
        print("등록된 프롬프트가 없습니다.")
        return

    sorted_prompts = sorted(prompts, key=lambda p: p["views"], reverse=True)

    for i, p in enumerate(sorted_prompts, start=1):
        star = " ⭐" if p["favorite"] else ""
        print(f"{i}. [{p['category']}] {p['title']}{star} - 조회수 {p['views']}")


# ------------------------------------------------------------
# 11. JSON으로 저장 (보너스: 영속화)
# ------------------------------------------------------------
def save_to_json(prompts, filename=JSON_FILE):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(prompts, f, ensure_ascii=False, indent=2)
        print(f"\n'{filename}' 파일로 저장되었습니다. (총 {len(prompts)}개)")
    except OSError as e:
        print(f"\n저장 중 오류가 발생했습니다: {e}")


# ------------------------------------------------------------
# 12. JSON 불러오기 (보너스: 영속화)
# ------------------------------------------------------------
def load_from_json(prompts, filename=JSON_FILE):
    if not os.path.exists(filename):
        print(f"\n'{filename}' 파일이 존재하지 않습니다.")
        return

    try:
        with open(filename, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        prompts.clear()
        prompts.extend(loaded)
        print(f"\n'{filename}' 파일에서 {len(loaded)}개의 프롬프트를 불러왔습니다.")
    except (OSError, json.JSONDecodeError) as e:
        print(f"\n불러오는 중 오류가 발생했습니다: {e}")


# ------------------------------------------------------------
# 13. 카테고리별 Markdown 내보내기 (보너스: 영속화)
# ------------------------------------------------------------
def export_markdown(prompts, export_dir=EXPORT_DIR):
    if not prompts:
        print("\n내보낼 프롬프트가 없습니다.")
        return

    os.makedirs(export_dir, exist_ok=True)

    grouped = {}
    for p in prompts:
        grouped.setdefault(p["category"], []).append(p)

    exported_files = []
    for category, items in grouped.items():
        safe_name = category.replace(" ", "_")
        filepath = os.path.join(export_dir, f"{safe_name}.md")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# {category} 프롬프트 모음\n\n")
            for p in items:
                star = " ⭐" if p["favorite"] else ""
                f.write(f"## {p['title']}{star}\n\n")
                f.write(f"{p['content']}\n\n")
                f.write(f"- 조회수: {p['views']}\n\n")
                f.write("---\n\n")

        exported_files.append(filepath)

    print(f"\n다음 파일로 내보내기 완료:")
    for path in exported_files:
        print(f" - {path}")


# ------------------------------------------------------------
# 메인 루프
# ------------------------------------------------------------
def main():
    prompts = create_default_prompts()

    actions = {
        "1": lambda: add_prompt(prompts),
        "2": lambda: show_list(prompts),
        "3": lambda: show_by_category(prompts),
        "4": lambda: search_prompt(prompts),
        "5": lambda: show_detail(prompts),
        "6": lambda: toggle_favorite(prompts),
        "7": lambda: show_favorites(prompts),
        "8": lambda: edit_prompt(prompts),
        "9": lambda: delete_prompt(prompts),
        "10": lambda: show_top_viewed(prompts),
        "11": lambda: save_to_json(prompts),
        "12": lambda: load_from_json(prompts),
        "13": lambda: export_markdown(prompts),
    }

    while True:
        show_menu()
        choice = input("선택: ").strip()

        if choice == "0":
            print("\n프로그램을 종료합니다. 이용해주셔서 감사합니다!")
            break

        action = actions.get(choice)
        if action is None:
            print("\n잘못된 번호입니다. 다시 선택해주세요.")
            continue

        action()


if __name__ == "__main__":
    main()
