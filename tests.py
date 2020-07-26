
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import os


gauth = GoogleAuth()
# gauth.LocalWebserverAuth()
gauth.LoadCredentialsFile("mycreds.txt")
if gauth.credentials is None:
    # This is what solved the issues:
    gauth.GetFlow()
    gauth.flow.params.update({'access_type': 'offline'})
    gauth.flow.params.update({'approval_prompt': 'force'})

    # Authenticate if they're not there
    gauth.LocalWebserverAuth()
elif gauth.access_token_expired:

    # Refresh them if expired
    gauth.Refresh()
else:

    # Initialize the saved creds
    gauth.Authorize()

# Save the current credentials to a file
gauth.SaveCredentialsFile("mycreds.txt")

drive = GoogleDrive(gauth)

#, item_name: str = None
def list_googledrive(image_suffix: str = None):
    #1pdSuEh1DgK0r2qFnpRGZHxv8nDuGz2z8

    all_folders = {
        "Graphic": "1kfBh-OKe27CMOTCM2KL8mmELVMKo4koe",
        "Speech": "16NGDpT4pX6JqvCbgMLFuLRJudq40FJNi",
        "SFX": "1aI0ui6L9uVo8RorNkXjTRUWi9hIaXdul"
    }

    if not image_suffix:
        for folder, folder_id in all_folders.items():
            files = drive.ListFile({'q': "'%s' in parents and trashed=false" % folder_id}).GetList()
            print(f"Category: {folder}")
            for file in files:
                print(f"Item name: {file['title']:<30} | ID: {file['id']}")
    else:

        for key, item in all_folders.items():
            if image_suffix == key:
                files = drive.ListFile({'q': "'%s' in parents and trashed=false" % item}).GetList()
                print(f"Category: {image_suffix}")
                for file in files:
                    #embed.add_field(name=f"Name: {file['title']}", value=f"ID: {file['id']}", inline=False)
                    print(f"Item name: {file['title']:<100} | ID: {file['id']}")
                break
        else:
            print("Category not found!")

#list_googledrive('1pdSuEh1DgK0r2qFnpRGZHxv8nDuGz2z8')

def list_spec():
    listed = drive.ListFile().GetList()
    print(listed)
    for file in listed:
        print(f"\033[34mTitle\033[m: \033[35m{file['title']:<70}\033[m| \033[34mID\033[m: \033[32m{file['id']}\033[m")


def list_spec2(parent):
    filelist = []
    file_list = drive.ListFile({'q': "'%s' in parents and trashed=false" % parent}).GetList()
    for f in file_list:
        if f['mimeType'] == 'application/vnd.google-apps.folder':  # if folder
            filelist.append({"id": f['id'], "title": f['title'], "list": list_spec2(f['id'])})
        else:
            # filelist.append({"title": f['title'],"id": f['id'] ,"title1": f['alternateLink']})
            filelist.append({"title": f['title'], "id": f['id']})
        print(f"{filelist[0]['title']} {filelist[0]['id']} - {len(file_list)} files in it")
        if len(file_list) != 0:
            #print(file_list)
            for file in file_list:
                print(
                    f"Title: {file['title']:<70} | ID: {file['id']}")
        else:
            print("Empty folder!")


list_spec2('144Wqi75ktpUNwg7mN6QnuciyVYwD7fee')
#list_googledrive('')