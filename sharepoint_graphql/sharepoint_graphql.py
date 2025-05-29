from os import PathLike
from io import StringIO
from typing import Iterator
from urllib.parse import urlparse

import requests
import msal
import json
import os


class ConnectionError(Exception):
    def __init__(self, message):
        super().__init__(message)
        print(f"ConnectionError: {message}")


class SecurityError(Exception):
    def __init__(self, message):
        super().__init__(message)
        print(f"SecurityError: {message}")


class TransactionError(Exception):
    def __init__(self, message):
        super().__init__(message)
        print(f"TransactionError: {message}")


class SharePointGraphql:
    """
    Handles interaction with the SharePoint site using Microsoft Graph API.

    The `SharePointGraphql` class simplifies actions like retrieving metadata,
    uploading files, moving files, deleting files, and downloading files through
    direct API calls to Microsoft Graph. It includes methods for authenticating
    and setting up the connection with SharePoint, and utility methods for
    managing file and folder operations.

    :ivar access_token: Authentication token for connecting to the Microsoft Graph API.
    :type access_token: str
    :ivar site_url: The SharePoint site base URL in Graph API format.
    :type site_url: str
    :ivar site_id: The unique identifier of the SharePoint site.
    :type site_id: str
    :ivar documents_id: The unique identifier of the "Documents" repository in the SharePoint site.
    :type documents_id: str
    """
    DOWNLOAD_URL_KEY = '@microsoft.graph.downloadUrl'
    GRAPH_BASE_URL = 'https://graph.microsoft.com/v1.0'

    def __init__(self, site_url, tenant_id, client_id, client_secret):
        try:
            self.access_token = self._get_token(client_id, client_secret, tenant_id)
        except KeyError:
            raise SecurityError("Access token not found, please check your credentials")
        self.headers = {"Authorization": f"Bearer {self.access_token}"}

        self.site_url = self._convert_site_url_to_graph_format(site_url)
        self.site_id = self._get_site_id(self.headers, self.site_url)
        self.documents_id = self._get_document_id(self.headers)

    def _get_document_id(self, headers):
        url = f'{self.GRAPH_BASE_URL}/sites/{self.site_id}/drive/'
        res = requests.get(url, headers=headers).json()

        if 'error' in res:
            raise ConnectionError(res['error']['message'])
        return res['id']

    def _get_site_id(self, headers, site_url):
        url = f'{self.GRAPH_BASE_URL}/sites/{site_url}'
        res = requests.get(url, headers=headers).json()
        return res['id']

    @staticmethod
    def _convert_site_url_to_graph_format(site_url):
        if not site_url.startswith("https://"):
            raise ConnectionError("Invalid URL format. URL must start with 'https://'.")
        parts = site_url.split("/")
        graph_url = f"{parts[2]}:/{parts[3]}/{parts[4]}:/"
        return graph_url

    def _build_graph_url(self, remote_path: str, action: str = "") -> str:
        """
        Constructs a Microsoft Graph API URL for a given remote path and action.

        :param remote_path: The relative path of the file or folder in SharePoint.
        :param action: The action to perform (e.g., 'content' for upload/download).
        :return: A formatted URL string.
        """
        remote_path = remote_path.strip("/")
        if action == 'content':
            url = f"{self.GRAPH_BASE_URL}/sites/{self.site_id}/drive/root:/{remote_path}:/{action}"
        else:
            url = f"{self.GRAPH_BASE_URL}/sites/{self.site_id}/drive/root:/{remote_path}"
        return url

    def _get_token(self, client_id, client_secret, tenant_id):
        authority_url = f'https://login.microsoftonline.com/{tenant_id}'
        app = msal.ConfidentialClientApplication(
            authority=authority_url,
            client_id=f'{client_id}',
            client_credential=f'{client_secret}'
        )
        token = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        return token['access_token']

    def list_files(self, folder_path: str):
        """
        Retrieves a list of files from a specified folder in a OneDrive account, using the
        Microsoft Graph API.

        The function sends HTTP GET requests to fetch file metadata collection in the
        provided folder path. Results are paginated through the Graph API `@odata.nextLink`
        property, and the function iterates until all pages have been processed.

        :param folder_path: The folder path in the OneDrive structure from which the files
            need to be listed.
        :type folder_path: str
        :return: A list containing metadata of files from the folder. Each file's data is
            represented as a dictionary.
        :rtype: list
        :raises HTTPError: If there is a networking issue or the API request fails.
        :raises JSONDecodeError: If the API returns invalid JSON in the body.
        """
        folder_path = folder_path.strip("/")

        url = f"{self.GRAPH_BASE_URL}/drives/{self.documents_id}/root:/{folder_path}:/children"
        files = []
        while True:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()  # Raise exception for non-200 status codes

            data = response.json()
            files.extend(data.get("value", []))
            if '@odata.nextLink' in data:
                url = data['@odata.nextLink']
            else:
                break
        return files

    def upload_file_by_relative_path(self, remote_path, local_path):
        """
        Uploads a file to a remote location specified by its relative path. The
        file content is read from the local file system and then uploaded to the
        remote server using an HTTP PUT request.

        The method constructs the URL based on the provided remote path and uses
        the configured headers to authenticate the request.

        :param remote_path: Relative path on the remote server where the file
            will be uploaded. Include the file name and extension.
        :type remote_path: str
        :param local_path: Absolute or relative path of the local file that
            needs to be uploaded.
        :type local_path: str
        :return: None
        """
        with open(local_path, "rb") as f:
            url = self._build_graph_url(remote_path, "content")
            response = requests.put(url, headers=self.headers, stream=True, data=f.read())
        response.raise_for_status()

    def move_file(self, remote_src_path, remote_des_path):
        """
        Moves a file from a source location to a destination location on a remote server.
        This method constructs a payload for the destination path, executes a move request
        to transfer the file, and raises an error if issues occur during the process.

        :param remote_src_path: The path to the file on the remote server to be moved.
        :type remote_src_path: str
        :param remote_des_path: The new destination path for the file on the remote server.
        :type remote_des_path: str
        :return: None
        :rtype: None
        :raises TransactionError: If an HTTP error occurs during the file move operation.
        """
        payload = self._build_move_destination_payload(remote_des_path)

        try:
            self._execute_move_request(payload, remote_src_path)
        except requests.exceptions.HTTPError as e:
            raise TransactionError(f"Error moving file: {e}")

    def _build_move_destination_payload(self, remote_des_path):
        new_filename = os.path.basename(remote_des_path)
        path = os.path.dirname(remote_des_path)
        # Construct the path reference
        path_reference = f"drives/{self.documents_id}/root:/{path}"
        # Payload for the move request
        payload = {
            "parentReference": {
                'path': path_reference
            },
            "name": new_filename
        }
        return payload

    def _execute_move_request(self, payload, remote_src_path):
        response = requests.patch(self._build_graph_url(remote_src_path), headers=self.headers, stream=True,
                                  json=payload)
        response.raise_for_status()

    def delete_file_by_relative_path(self, remote_path: str):
        """
        Deletes a file from the SharePoint site by its relative path.

        This method sends a DELETE request to the Microsoft Graph API to remove the specified file.

        :param remote_path: The relative path of the file to be deleted on the SharePoint site.
        :type remote_path: str
        :raises TransactionError: If the API request fails or returns an error.
        :return: None
        """

        try:
            response = requests.delete(self._build_graph_url(remote_path), headers=self.headers)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise TransactionError(f"Error deleting file: {e}")

    @staticmethod
    def _setup_local_directory(output_path: os.PathLike) -> PathLike:
        output_path = SharePointGraphql._resolve_absolute_path(output_path)
        SharePointGraphql._ensure_directory_exists(output_path)
        return output_path

    @staticmethod
    def _resolve_absolute_path(output_path: os.PathLike) -> os.PathLike:
        if not os.path.isabs(output_path):
            output_path = os.path.join(os.getcwd(), output_path)
        return output_path

    @staticmethod
    def _ensure_directory_exists(output_path: os.PathLike):
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def download_file(self, url: str, output_path: os.PathLike):
        """
        Downloads a file from a specified URL and saves it to the given path.

        This function retrieves the file from the specified URL and writes it to a local
        path. A directory is setup or verified before storing the file. The function streams
        the data in chunks to handle large files efficiently.

        :param url: The URL of the file to download.
        :type url: str
        :param output_path: The destination local path to save the downloaded file. This can
                           be a file path string or any object implementing os.PathLike.
        :type output_path: os.PathLike
        :return: None
        :rtype: None
        :raises TransactionError: If there is an HTTP error during the file download.
        """
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()  # Raise an exception for non-2xx status codes
        except requests.exceptions.HTTPError as e:
            raise TransactionError(f"Error downloading file: {e}")

        with open(self._setup_local_directory(output_path), "wb") as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)

    def is_valid_url(self, url: str) -> bool:
        """
        Validate if the URL is well-formed and belongs to the trusted domain.
        :param url: URL to validate.
        :param trusted_domain: Trusted domain to check against.
        :return: True if URL is valid and belongs to the trusted domain, False otherwise.
        """
        trusted_domain = "sharepoint.com"
        try:
            parsed_url = urlparse(url)
            return parsed_url.scheme in ["http", "https"] and parsed_url.netloc.endswith(
                trusted_domain
            )
        except Exception:
            return False

    def download_filestream(self, remote_file_path: str) -> StringIO:
        """
        Downloads a file from a specified URL and returns the response object.

        :param remote_file_path: The file path of the file to download.
        :type remote_file_path: str
        :return: A file object if download is successful.
        :rtype: StringIO
        :raises TransactionError: If there is an issue with the HTTP request.
        """
        url = self._build_graph_url(remote_file_path)
        download_url = self._get_download_url(url)
        return self._download_to_stream(download_url)

    def _get_download_url(self, url: str) -> str:
        try:
            response = self._retry_request("GET", url, headers=self.headers)
            response_data = response.json()
            download_url = response_data[self.DOWNLOAD_URL_KEY]
            if not self.is_valid_url(download_url):
                raise TransactionError(f"Invalid download URL: {download_url}")
            return download_url
        except requests.exceptions.RequestException as e:
            raise TransactionError(f"Error retrieving file metadata: {e}")

    def _download_to_stream(self, download_url: str) -> StringIO:
        try:
            response = self._retry_request("GET", download_url, stream=True)
            file_stream = StringIO()
            file_stream.write(response.content.decode("utf-8"))
            file_stream.seek(0)
            return file_stream
        except requests.exceptions.RequestException as e:
            raise TransactionError(f"Error downloading file: {e}")

    def _retry_request(self, method: str, url: str, **kwargs) -> requests.Response:
        for _ in range(3):  # Retry up to 3 times
            response = requests.request(method, url, **kwargs)
            if response.status_code < 500:  # Retry only for server errors
                return response
            time.sleep(5)  # Delay between retries
        response.raise_for_status()

    def download_file_by_relative_path(self, remote_path: str, local_path: os.PathLike):
        """
            Downloads a file from the SharePoint site by its relative path.

            This method retrieves the file's download URL using the Microsoft Graph API
            and then downloads the file to the specified local path.

            Args:
                remote_path: The relative path of the file on the SharePoint site.
                local_path: The local file path where the downloaded file should be saved.

            Raises:
                KeyError: If the download URL is not found in the API response.
                requests.exceptions.RequestException: If there is an issue with the HTTP request.
        """

        response = requests.get(self._build_graph_url(remote_path), headers=self.headers)
        response.raise_for_status()
        data = response.json()

        if self.DOWNLOAD_URL_KEY not in data:
            raise KeyError("Download URL not found in response")
        self.download_file(data[self.DOWNLOAD_URL_KEY], local_path)
