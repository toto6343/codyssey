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

def edit_prompt(prompts):
    pass


def delete_prompt(prompts):
    pass


def show_top_viewed(prompts):
    pass


def save_to_json(prompts, filename=JSON_FILE):
    pass


def load_from_json(prompts, filename=JSON_FILE):
    pass


def export_markdown(prompts, export_dir=EXPORT_DIR):
    pass


# ------------------------------------------------------------
# 메인 함수
# ------------------------------------------------------------
def main():
    prompts = []

    while True:
        show_menu()
        choice = input("선택: ")

        if choice == "0":
            print("프로그램을 종료합니다.")
            break

        elif choice == "1":
            add_prompt(prompts)
        elif choice == "2":
            show_list(prompts)
        elif choice == "3":
            show_by_category(prompts)
        elif choice == "4":
            search_prompt(prompts)
        elif choice == "5":
            show_detail(prompts)
        elif choice == "6":
            toggle_favorite(prompts)
        elif choice == "7":
            show_favorites(prompts)
        elif choice == "8":
            edit_prompt(prompts)
        elif choice == "9":
            delete_prompt(prompts)
        elif choice == "10":
            show_top_viewed(prompts)
        elif choice == "11":
            save_to_json(prompts)
        elif choice == "12":
            load_from_json(prompts)
        elif choice == "13":
            export_markdown(prompts)
        else:
            print("잘못된 메뉴입니다.")


if __name__ == "__main__":
    main()