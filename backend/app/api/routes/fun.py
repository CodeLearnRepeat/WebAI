import sys

def main():
    futtocks()

def futtocks():
    charecter = input("Do you wish to be the admiral or the young officer? (admiral or young officer) ").strip().lower()
    if charecter == 'young officer':
        young_officer_dialog()
    elif charecter == 'admiral':
        admiral_dialog()
    else:
        sys.exit("Not even close")

def young_officer_dialog():
    admiral = input("What do you decide to say to the admiral (only one right answer): ").strip().lower()
    if admiral == "how are your futtocks old man":
        print("At their farthest reach, dear boy, at their farthest reach.")
    else:
        sys.exit("Not even close")

def admiral_dialog():
    young_officer = input("What do you say in response to 'how are your futtocks old man'?(Only ONE right answer): ")
    if young_officer == "At their farthest reach, dear boy, at their farthest reach." or young_officer == "at their farthest reach":
        print("Indeed, salty engish admiral, with overstreched futtocks")
    else:
        sys.exit("Not even close")

if __name__ == "__main__":
    main()
