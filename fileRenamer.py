import os


def replace_substring_in_files_single_root():
    folderName = input("Enter Path of Folder to change names within: ")
    oldChar = input("Enter Characters to replace in File Names: ")
    newChar = input("Enter Characters to replace with in File Names: ")
    filesPaths = []

    for (root,dirs,files) in os.walk(folderName):
        for file in files:
            filesPaths.append(os.path.join(root,file))
    print('Files Changed: \n')
    for path in filesPaths:
        newname = path.replace(oldChar, newChar)
        if newname != path:
            os.rename(path, newname)
            print(newname)

def replace_substring_in_filename_multiroot():
    oldChar = input("Enter Characters to replace in File Names: ")
    newChar = input("Enter Characters to replace with in File Names: ")
    filesPaths = []
    folderNames = [r'C:\Users\Vijay\Documents\GitHub\Fracktory-5\resources\intent\base_fracktal_printer\ABS\Model 0.6',r'C:\Users\Vijay\Documents\GitHub\Fracktory-5\resources\intent\base_fracktal_printer\CF-Nylon\Model 0.6',r'C:\Users\Vijay\Documents\GitHub\Fracktory-5\resources\intent\base_fracktal_printer\Nylon\Model 0.6',r'C:\Users\Vijay\Documents\GitHub\Fracktory-5\resources\intent\base_fracktal_printer\PETG\Model 0.6',r'C:\Users\Vijay\Documents\GitHub\Fracktory-5\resources\intent\base_fracktal_printer\PLA\Model 0.6']

    for folderName in folderNames:
         for (root,dirs,files) in os.walk(folderName):
            for file in files:
                filesPaths.append(os.path.join(root,file))
    print('Files Changed: \n')
    for path in filesPaths:
        newname = path.replace(oldChar, newChar)
        if newname != path:
            os.rename(path, newname)
            print(newname)

def find_and_replace_in_files_matching_substring():
    """
    Finds and replaces a string in all files within a folder tree where the file name contains a specific substring.

    :param base_folder: The base folder to start the search from.
    :param search_string: The string to search for in the files.
    :param replace_string: The string to replace the search string with.
    :param filename_substring: The substring that the file names should contain for the replacement to be performed.
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

    find_and_replace_in_files_matching_substring()