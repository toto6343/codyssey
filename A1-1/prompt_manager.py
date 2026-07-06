# -*- coding: utf-8 -*-

import json
import os

# ------------------------------------------------------------
# 상수 정의
# ------------------------------------------------------------
CATEGORIES = ["텍스트 생성", "이미지 생성", "영상 생성", "페르소나", "자동화", "기타"]
JSON_FILE = "prompts.json"
EXPORT_DIR = "exports"


# ------------------------------------------------------------
# 기본 데이터
# ------------------------------------------------------------
def create_default_prompts():
    pass


# ------------------------------------------------------------
# 공통 입력 함수
# ------------------------------------------------------------
def get_non_empty_input(label):
    pass


def choose_category():
    pass


def get_valid_index(prompts, label="번호 입력: "):
    pass


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
# 기능 함수
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
