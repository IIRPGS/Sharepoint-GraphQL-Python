import requests
import msal
import json
import os

GRAPH_URL = 'https://graph.microsoft.com/v1.0/'


class ConnectionError(Exception):
    """Custom exception for SharePoint GraphQL errors."""

    def __init__(self, message):
        self.message = message
        print(f"ConnectionError: {self.message}")
        raise self


class SecurityError(Exception):
    """Custom exception for SharePoint GraphQL errors."""

    def __init__(self, message):
        self.message = message
        print(f"SecurityError: {self.message}")
        raise self


# class ContentError(Exception):
#     """Custom exception for SharePoint GraphQL errors."""
#
#     def __init__(self, message):
#         self.message = message
#         print(f"ContentError: {self.message}")
#         raise self



class SharePointGraphql:

    def __init__(self, site_url, tenant_id, client_id, client_secret):
        try:
            self.access_token = self._get_token(client_id, client_secret, tenant_id)
        except KeyError:
            raise SecurityError("Access token not found, please check your credentials")
        headers = {"Authorization": f"Bearer {self.access_token}"}

        self.site_url = self._convert_site_url_to_graph_format(site_url)
        self.site_id = self._get_site_id(headers, self.site_url)
        self.documents_id = self._get_document_id(headers)

    def _get_document_id(self, headers):
        url = f'{GRAPH_URL}sites/{self.site_id}/drive/'
        res = json.loads(requests.get(url, headers=headers).text)

        if 'error' in res:
            raise ConnectionError(res['error']['message'])
        return res['id']

    def _get_site_id(self, headers, site_url):
        url = f'{GRAPH_URL}sites/{site_url}'
        res = json.loads(requests.get(url, headers=headers).text)
        return res['id']

    def _convert_site_url_to_graph_format(self, site_url):
        if not site_url.startswith("https://"):
            raise ConnectionError("Invalid URL format. URL must start with 'https://'.")
        parts = site_url.split("/")
        graph_url = f"{parts[2]}:/{parts[3]}/{parts[4]}:/"
        return graph_url

    def _get_token(self, client_id, client_secret, tenant_id):
        """
        Acquire token via MSAL
        """
        authority_url = f'https://login.microsoftonline.com/{tenant_id}'
        app = msal.ConfidentialClientApplication(
            authority=authority_url,
            client_id=f'{client_id}',
            client_credential=f'{client_secret}'
        )
        token = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        return token['access_token']

    def list_files(self, folder_path: str, next_link: str=None, files: list = None):
        """
        Lists files within a specific folder on the SharePoint site. (Max 5000 files)

        Args:
            folder_path: The server-relative path of the folder (e.g., "/sites/your-site/Shared Documents/subfolder").

        Returns:
            A list of dictionaries representing files, each containing properties like name, id, and downloadUrl.
            An empty list if there are no files or an error occurs.
        """
        if files is None:
            files = []

        url = f"{GRAPH_URL}drives/{self.documents_id}/root:/{folder_path}:/children"
        headers = {"Authorization": f"Bearer {self.access_token}"}

        # Why is this check here? Maybe because of the limitation of recursive function?
        # if len(files) > 5000:
        #     raise Exception("Too many files (Try to create subfolder)")
        try:
            if next_link is not None:
                url = next_link
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # Raise exception for non-200 status codes
            data = response.json()
            files += data.get("value", [])
            if '@odata.nextLink' in data:
                next_link = data['@odata.nextLink']
                return self.list_files(folder_path=folder_path, next_link=next_link, files=files)

            return files  # Extract "value" array containing files
        except requests.exceptions.RequestException as e:
            print(f"Error listing files: {e}")
            return []

    def list_files_non_recursive(self, folder_path: str):
        """
        Lists files in a specified folder non-recursively using Microsoft Graph API.

        This method retrieves the list of files and folders within the specified
        folder path without exploring subfolders. It uses pagination to handle
        responses that exceed the default limit and combines all the paginated
        results into a single list for the caller. The function requires a valid
        Microsoft Graph API access token to authenticate and access the desired
        folder.

        :param folder_path: The path of the folder whose files are to be listed
            non-recursively.
        :type folder_path: str
        :return: A list of dictionaries containing metadata of files and folders
            within the specified folder path.
        :rtype: list
        :raises ConnectionError: If there is an issue with the HTTP request, such as
            network problems or invalid API response.
        """
        url = f"{GRAPH_URL}drives/{self.documents_id}/root:/{folder_path}:/children"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        files = []
        while True:
            try:
                response = requests.get(url, headers=headers)
                response.raise_for_status()  # Raise exception for non-200 status codes
            except requests.exceptions.RequestException as e:
                raise ConnectionError(f"Error listing files: {e}")

            data = response.json()
            files.append(data.get("value", []))
            if '@odata.nextLink' in data:
                url = data['@odata.nextLink']
            else:
                break
        return files

    def download_file_by_relative_path(self, remote_path, local_path):
        """
        Downloads a file by its relative path from the SharePoint site.

        Args:
            remote_path: The file path of the file to download. (Relative path start after Documents)
            local_path: The file path of the destination your will save

        Returns:
            True if download file successful, False otherwise.
        """

        url = f"{GRAPH_URL}/sites/{self.site_id}/drive/root:/{remote_path}"

        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            response = requests.get(url, headers=headers, stream=True)
            response.raise_for_status()
            data = response.json()

            return self.download_file(data['@microsoft.graph.downloadUrl'], local_path)
        except (requests.exceptions.RequestException, KeyError) as e:
            print(f"Error downloading file: {e}")
            return False

    def upload_file_by_relative_path(self, remote_path, local_path):
        """
        Upload a file by its relative path from the SharePoint site.

        Args:
            remote_path: The file path of the file to upload. (Relative path start after Documents)
            local_path: The file path of the local file

        Returns:
            True if upload file successful, False otherwise.
        """

        url = f"{GRAPH_URL}/sites/{self.site_id}/drive/root:/{remote_path}:/content"

        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            with open(local_path, "rb") as f:
                response = requests.put(url, headers=headers, stream=True, data=f.read())
            response.raise_for_status()
            data = response.json()

            return True
        except (requests.exceptions.RequestException, KeyError, OSError) as e:
            print(f"Error Uploading file: {e}")
            return False

    def move_file(self, remote_src_path, remote_des_path):
        """
        Move a file by its source path to the destination from the SharePoint site.

        Args:
            remote_src_path: The remote file path of the source file
            remote_des_path: The remote file path of the destination file

        Returns:
            True if move file successful, False otherwise.
        """

        new_filename = os.path.basename(remote_des_path)
        path = os.path.dirname(remote_des_path)

        # Construct the path reference
        path_reference = f"drives/{self.documents_id}/root:/{path}"

        url = f"{GRAPH_URL}/sites/{self.site_id}/drive/root:/{remote_src_path}"

        headers = {"Authorization": f"Bearer {self.access_token}"}

        # Payload for the move request
        payload = {
            "parentReference": {
                'path': path_reference
            },
            "name": new_filename
        }

        try:
            response = requests.patch(url, headers=headers, stream=True, json=payload)
            response.raise_for_status()
            data = response.json()

            return True
        except (requests.exceptions.RequestException, KeyError) as e:
            print(f"Error downloading file: {e}")
            return None

    def delete_file_by_relative_path(self, remote_path):
        """
        Delete a file by its relative path from the SharePoint site.

        Args:
            remote_path: The file path of the file to delete. (Relative path start after Documents)

        Returns:
            True if delete file successful, False otherwise.
        """

        url = f"{GRAPH_URL}/sites/{self.site_id}/drive/root:/{remote_path}"

        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            response = requests.delete(url, headers=headers, stream=True)
            response.raise_for_status()

            return True
        except (requests.exceptions.RequestException, KeyError, OSError) as e:
            print(f"Error deleteing file: {e}")
            return False

    def download_file(self, url, output_path):
        """
        Downloads a file from a URL and saves it to the specified path.

        Args:
            url (str): The absolute URL of the file to download.
            output_path (str): The absolute path where the file will be saved.

        Returns:
            file: The file object of the downloaded file,
                or None if there was an error.

        Raises:
            OSError: If there's an issue creating the output directory or file.
            requests.exceptions.RequestException: If there's an error downloading the file.
        """

        # Get absolute path based on current working directory (for relative paths)
        if not os.path.isabs(output_path):
            output_path = os.path.join(os.getcwd(), output_path)

        # Check if output directory exists, create it if necessary
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Get the filename from the URL (consider using a library for robust extraction)
        filename = os.path.basename(url)

        # Download the file using requests
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()  # Raise an exception for non-2xx status codes

            # Open the output file in binary write mode
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:  # filter out keep-alive new chunks
                        f.write(chunk)

            return True  # Return the opened file object

        except (OSError, requests.exceptions.RequestException) as e:
            print(f"Error downloading file: {e}")
            return False
