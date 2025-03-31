import os


def replace_substring_in_filenames():
    """
    Replaces a substring in file names within a folder tree.
    """
    folder_name = input("Enter the path of the folder to change names within: ")
    old_char = input("Enter the characters to replace in file names: ")
    new_char = input("Enter the characters to replace with in file names: ")

    print('Files Changed: \n')
    for root, dirs, files in os.walk(folder_name):
        for file in files:
            old_path = os.path.join(root, file)
            new_path = old_path.replace(old_char, new_char)
            if new_path != old_path:
                os.rename(old_path, new_path)
                print(new_path)


def find_and_replace_in_files():
    """
    Finds and replaces a string in all files within a folder tree where the file name contains a specific substring.
    """
    base_folder = input("Enter the base folder path: ")
    search_string = input("Enter the string to search for: ")
    replace_string = input("Enter the string to replace with: ")
    filename_substring = input("Enter the substring that should be in the file names: ")

    for root, dirs, files in os.walk(base_folder):
        for file_name in files:
            if filename_substring in file_name:
                file_path = os.path.join(root, file_name)
                with open(file_path, 'r', encoding='utf-8') as file:
                    file_contents = file.read()

                new_contents = file_contents.replace(search_string, replace_string)

                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(new_contents)
                print(f"Replaced in: {file_path}")


if __name__ == "__main__":
    print("Choose the type of operation:")
    print("1. Replace substring in file names within a folder tree")
    print("2. Find and replace text in files matching a specific substring in their names")
    choice = input("Enter your choice (1/2): ")

    if choice == "1":
        replace_substring_in_filenames()
    elif choice == "2":
        find_and_replace_in_files()
    else:
        print("Invalid choice. Exiting.")