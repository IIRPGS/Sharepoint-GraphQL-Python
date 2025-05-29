import json
import os
import pathlib
from io import TextIOWrapper

import pytest
from unittest.mock import MagicMock

import requests

import sharepoint_graphql.sharepoint_graphql
from sharepoint_graphql import SharePointGraphql, ConnectionError, TransactionError
from sharepoint_graphql.sharepoint_graphql import SecurityError


class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data

    @property
    def text(self):
        return json.dumps(self.json_data)

    def raise_for_status(self):
        if self.status_code != 200:
            raise ConnectionError("Mocked error")


class MockResponseTransactionError:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data

    @property
    def text(self):
        return json.dumps(self.json_data)

    def raise_for_status(self):
        if self.status_code != 200:
            raise requests.exceptions.HTTPError("Mocked error")


@pytest.fixture
def mock_client():
    return {
        "site_url": "https://mycompany.sharepoint.com/sites/warehouse",
        "tenant_id": "test_tenant",
        "client_id": "test_client",
        "client_secret": "test_secret"
    }


# @pytest.fixture
# def mock_client_failure():
#     return {
#         "site_url": "https://mycompany.sharepoint.com/sites/warehouse",
#         "tenant_id": "test_tenant",
#         "client_id": "test_client",
#         "client_secret": "test_secret"
#     }


@pytest.fixture
def mock_error_message():
    return "An error occurred"


@pytest.fixture
def mock_object(mock_client, monkeypatch):
    mock_token = "mock_access_token"
    # mock_site_url = "mock_graph_site_url"
    mock_site_id = "mock_site_id"
    mock_documents_id = "mock_documents_id"

    monkeypatch.setattr(SharePointGraphql, "_get_token", MagicMock(return_value=mock_token))
    # monkeypatch.setattr(SharePointGraphql, "_convert_site_url_to_graph_format", MagicMock(return_value=mock_site_url))
    monkeypatch.setattr(SharePointGraphql, "_get_site_id", MagicMock(return_value=mock_site_id))
    monkeypatch.setattr(SharePointGraphql, "_get_document_id", MagicMock(return_value=mock_documents_id))

    sharepoint_graphql = SharePointGraphql(**mock_client)
    return sharepoint_graphql


@pytest.fixture
def mock_object_for_testing_site_id(mock_client, monkeypatch):
    mock_token = "mock_access_token"
    mock_site_url = "mock_graph_site_url"
    # mock_site_id = "mock_site_id"
    mock_documents_id = "mock_documents_id"

    monkeypatch.setattr(SharePointGraphql, "_get_token", MagicMock(return_value=mock_token))
    monkeypatch.setattr(SharePointGraphql, "_convert_site_url_to_graph_format", MagicMock(return_value=mock_site_url))
    # monkeypatch.setattr(SharePointGraphql, "_get_site_id", MagicMock(return_value=mock_site_id))
    monkeypatch.setattr(SharePointGraphql, "_get_document_id", MagicMock(return_value=mock_documents_id))

    mock_response = {
        "id": "mock_site_id"
    }
    def mock_get(url, headers):
        print(f"Mocked GET request to URL: {url} with headers: {headers}")
        return MockResponse(mock_response, 200)

    monkeypatch.setattr("requests.get", mock_get)

    sharepoint_graphql = SharePointGraphql(**mock_client)
    return sharepoint_graphql



@pytest.fixture
def mock_object_for_testing_document_id(mock_client, monkeypatch):
    mock_token = "mock_access_token"
    # mock_site_url = "mock_graph_site_url"
    mock_site_id = "mock_site_id"
    mock_documents_id = "mock_documents_id"

    mock_response = {
        "id": mock_documents_id,
    }

    def mock_get(url, headers):
        print(f"Mocked GET request to URL: {url} with headers: {headers}")
        return MockResponse(mock_response, 200)

    monkeypatch.setattr("requests.get", mock_get)

    monkeypatch.setattr(SharePointGraphql, "_get_token", MagicMock(return_value=mock_token))
    # monkeypatch.setattr(SharePointGraphql, "_convert_site_url_to_graph_format", MagicMock(return_value=mock_site_url))
    monkeypatch.setattr(SharePointGraphql, "_get_site_id", MagicMock(return_value=mock_site_id))
    # monkeypatch.setattr(SharePointGraphql, "_get_document_id", MagicMock(return_value=mock_documents_id))

    sharepoint_graphql = SharePointGraphql(**mock_client)
    return sharepoint_graphql


@pytest.fixture
def mock_object_for_testing_token(mock_client, monkeypatch):
    mock_token = "mock_access_token"
    mock_site_url = "mock_graph_site_url"
    mock_site_id = "mock_site_id"
    mock_documents_id = "mock_documents_id"

    class MockConfidentialClientApplication:
        def __init__(self, authority, client_id, client_credential):
            pass

        def acquire_token_for_client(self, scopes):
            return {"access_token": "mock_access_token"}

    monkeypatch.setattr("msal.ConfidentialClientApplication", MockConfidentialClientApplication)

    # monkeypatch.setattr(SharePointGraphql, "_get_token", MagicMock(return_value=mock_token))
    monkeypatch.setattr(SharePointGraphql, "_convert_site_url_to_graph_format", MagicMock(return_value=mock_site_url))
    monkeypatch.setattr(SharePointGraphql, "_get_site_id", MagicMock(return_value=mock_site_id))
    monkeypatch.setattr(SharePointGraphql, "_get_document_id", MagicMock(return_value=mock_documents_id))

    sharepoint_graphql = SharePointGraphql(**mock_client)
    return sharepoint_graphql


def test_connectionerror_handling(mock_error_message):
    # Arrange
    def function_that_raises(mock_error_message):
        raise ConnectionError(mock_error_message)

    # Act & Assert
    with pytest.raises(ConnectionError, match=mock_error_message) as exc_info:
        function_that_raises(mock_error_message)

    assert str(exc_info.value) == mock_error_message


def test_securityerror_handling(mock_error_message):
    # Arrange
    def function_that_raises(mock_error_message):
        raise SecurityError(mock_error_message)

    # Act & Assert
    with pytest.raises(SecurityError, match=mock_error_message) as exc_info:
        function_that_raises(mock_error_message)

    assert str(exc_info.value) == mock_error_message


def test_sharepoint_graphql_instantiation_with_invalid_mocked_token(mock_client, monkeypatch):
    # Arrange
    mock_token = "mock_access_token"

    def mock_get_token(self, client_id, client_secret, tenant_id):
        raise KeyError("Access token not found, please check your credentials")

    monkeypatch.setattr(SharePointGraphql, "_get_token", mock_get_token)
    monkeypatch.setattr(SharePointGraphql, "_convert_site_url_to_graph_format", MagicMock(return_value="site_url"))
    monkeypatch.setattr(SharePointGraphql, "_get_site_id", MagicMock(return_value="site_id"))
    monkeypatch.setattr(SharePointGraphql, "_get_document_id", MagicMock(return_value="documents_id"))
    # Act
    with pytest.raises(SecurityError, match="Access token not found, please check your credentials"):
        SharePointGraphql(**mock_client)


def test_sharepoint_graphql_instantiation_with_mocked_token(mock_client, monkeypatch):
    # Arrange
    mock_token = "mock_access_token"
    mock_site_url = "mock_graph_site_url"
    mock_site_id = "mock_site_id"
    mock_documents_id = "mock_documents_id"

    # def mock_get_token(self, client_id, client_secret, tenant_id):
    #     return mock_token

    monkeypatch.setattr(SharePointGraphql, "_get_token", MagicMock(return_value=mock_token))
    monkeypatch.setattr(SharePointGraphql, "_convert_site_url_to_graph_format", MagicMock(return_value=mock_site_url))
    monkeypatch.setattr(SharePointGraphql, "_get_site_id", MagicMock(return_value=mock_site_id))
    monkeypatch.setattr(SharePointGraphql, "_get_document_id", MagicMock(return_value=mock_documents_id))

    # Act
    sharepoint_graphql = SharePointGraphql(**mock_client)

    # Assert
    assert sharepoint_graphql.access_token == mock_token
    assert sharepoint_graphql.site_url == mock_site_url
    assert sharepoint_graphql.site_id == mock_site_id
    assert sharepoint_graphql.documents_id == mock_documents_id


def test_sharepoint_graphql__convert_site_url_to_graph_format_success(mock_object):
    # Arrange
    assigned_site_url = "https://mycompany.sharepoint.com/sites/warehouse"
    expected_site_url = "mycompany.sharepoint.com:/sites/warehouse:/"

    # Act
    site_url = mock_object._convert_site_url_to_graph_format(assigned_site_url)

    # Assert
    assert site_url == expected_site_url


def test_sharepoint_graphql__convert_site_url_to_graph_format_failure(mock_object):
    # Arrange
    assigned_site_url = "http://mycompany.sharepoint.com/sites/warehouse"

    # Act & Assert
    with pytest.raises(ConnectionError, match="Invalid URL format. URL must start with 'https://'.") as exc_info:
        mock_object._convert_site_url_to_graph_format(assigned_site_url)


def test_sharepointgraphql__get_site_id_success(mock_object_for_testing_site_id, monkeypatch):
    # Arrange
    mock_site_url = "https://mycompany.sharepoint.com/sites/warehouse"
    expected_site_id = "a_mock_site_id"
    mock_response = {
        "id": expected_site_id
    }

    def mock_get(url, headers):
        print(f"Mocked GET request to URL: {url} with headers: {headers}")
        return MockResponse(mock_response, 200)

    monkeypatch.setattr("requests.get", mock_get)

    # Act
    site_id = mock_object_for_testing_site_id._get_site_id("mock_access_token", mock_site_url)

    # Assert
    assert site_id == expected_site_id


def test_sharepointgraphql__get_document_id_success(mock_object_for_testing_document_id, monkeypatch):
    # Arrange
    expected_document_id = "a_mock_documents_id"
    mock_response = {
        "id": expected_document_id
    }

    def mock_get(url, headers):
        print(f"Mocked GET request to URL: {url} with headers: {headers}")
        return MockResponse(mock_response, 200)

    monkeypatch.setattr("requests.get", mock_get)

    # Act
    document_id = mock_object_for_testing_document_id._get_document_id("mock_access_token")

    # Assert
    assert document_id == expected_document_id


def test_sharepointgraphql__get_document_id_failure(mock_object_for_testing_document_id, monkeypatch):
    # Arrange
    error_response = {
        "error": {
            "code": "InvalidRequest",
            "message": "Invalid request"
        }
    }

    def mock_get(url, headers):
        return MockResponse(error_response, 400)

    monkeypatch.setattr("requests.get", mock_get)

    # Act & Assert
    with pytest.raises(ConnectionError) as exc_info:
        mock_object_for_testing_document_id._get_document_id("mock_access_token")

    assert str(exc_info.value) == "Invalid request"


def test_sharepointgraphql_list_files_success(mock_object, monkeypatch):
    # Arrange
    folder_path = "Documents/Folder"
    first_response = {
        "value": [
            {"name": "file1.txt", "id": "1"},
            {"name": "file2.txt", "id": "2"}
        ],
        "@odata.nextLink": "https://graph.microsoft.com/v1.0/nextPage"
    }
    second_response = {
        "value": [
            {"name": "file3.txt", "id": "3"},
            {"name": "file4.txt", "id": "4"}
        ]
    }

    def mock_get(url, headers):
        if url == f"https://graph.microsoft.com/v1.0/drives/mock_documents_id/root:/Documents/Folder:/children":
            return MockResponse(first_response, 200)
        elif url == "https://graph.microsoft.com/v1.0/nextPage":
            return MockResponse(second_response, 200)
        else:
            raise ConnectionError("Unexpected URL")

    monkeypatch.setattr("requests.get", mock_get)

    # Act
    files = mock_object.list_files(folder_path)

    # Assert
    assert len(files) == 4
    assert files[0]["name"] == "file1.txt"
    assert files[1]["name"] == "file2.txt"
    assert files[2]["name"] == "file3.txt"
    assert files[3]["name"] == "file4.txt"


def test_sharepointgraphql_list_files_failure(mock_object, monkeypatch):
    # Arrange
    folder_path = "Documents/Folder"
    error_response = {
        "error": {
            "code": "InvalidRequest",
            "message": "Invalid request"
        }
    }

    def mock_get(url, headers):
        return MockResponse(error_response, 400)

    monkeypatch.setattr("requests.get", mock_get)

    # Act & Assert
    with pytest.raises(ConnectionError) as exc_info:
        mock_object.list_files(folder_path)

    assert str(exc_info.value) == "Mocked error"


def test_sharepointgraphql__resolve_absolute_path(mock_object, monkeypatch):
    # Arrange
    full_folder_path = pathlib.PurePath("/root/Folder")
    partial_folder_path = pathlib.PurePath("Folder")
    expected_path_full_path = pathlib.PurePath("/root/Folder")

    def mock_getcwd(*args):
        return "/root"

    monkeypatch.setattr("os.getcwd", mock_getcwd)

    # Act
    test_path_full = mock_object._resolve_absolute_path(full_folder_path)
    test_path_partial = mock_object._resolve_absolute_path(partial_folder_path)

    # Change the expected path to match the operating system
    if os.name == 'nt':  # For Windows
        test_path_partial = str(test_path_partial).replace("\\", "/")
        test_path_partial = pathlib.PurePath(test_path_partial)

    # Assert
    assert test_path_full == expected_path_full_path
    assert test_path_partial == expected_path_full_path


def test_sharepointgraphql_ensure_directory_exists(mock_object, monkeypatch, capsys):
    # Arrange
    if os.name == 'nt':  # For Windows
        directory_path_exists = os.path.join(os.environ.get('TEMP'), 'file.txt')
    else:  # For Unix-like systems
        directory_path_exists = "/tmp/file.txt"

    directory_path_not_exists = "/tmp/not_exists/file.txt"

    expected_output_directory_does_not_exist = "Mocked os.makedirs\n"

    def mock_makedirs(file_path):
        print("Mocked os.makedirs")

    monkeypatch.setattr("os.makedirs", mock_makedirs)

    # Act
    mock_object._ensure_directory_exists(directory_path_exists)
    captured_path_exists = capsys.readouterr()

    mock_object._ensure_directory_exists(directory_path_not_exists)
    captured_path_does_not_exist = capsys.readouterr()

    # Assert
    assert captured_path_exists.out == ''
    assert captured_path_does_not_exist.out == expected_output_directory_does_not_exist


def test_sharepointgraphql__setup_local_directory(mock_object, monkeypatch):
    # Arrange
    output_path = pathlib.PurePath("test_directory/test_file.txt")
    expected_output_path = os.path.abspath(output_path)

    def mock_ensure_directory_exists(file_path):
        pass

    monkeypatch.setattr("sharepoint_graphql.SharePointGraphql._ensure_directory_exists", mock_ensure_directory_exists)

    # Act
    result = mock_object._setup_local_directory(output_path)

    # Assert
    assert result == expected_output_path


def test_sharepointgraphql_download_file_success(mock_object, monkeypatch):
    # Arrange
    test_url = "https://example.com/test.txt"
    test_output_path = "test/output/file.txt"
    mock_absolute_path = "/absolute/path/to/test/output/file.txt"
    mock_content = b"test content"

    # Mock the setup_local_directory method
    monkeypatch.setattr(
        mock_object,
        "_setup_local_directory",
        MagicMock(return_value=mock_absolute_path)
    )

    # Mock requests.get to return a response that can be iterated for content
    mock_response = MagicMock()
    mock_response.iter_content.return_value = [mock_content]
    monkeypatch.setattr(
        "requests.get",
        MagicMock(return_value=mock_response)
    )

    # Mock open function to avoid actual file operations
    mock_file = MagicMock(spec=TextIOWrapper)
    mock_open = MagicMock(return_value=mock_file)
    monkeypatch.setattr("builtins.open", mock_open)

    # Act
    mock_object.download_file(test_url, test_output_path)

    # Assert
    mock_object._setup_local_directory.assert_called_once_with(test_output_path)
    mock_response.raise_for_status.assert_called_once()
    mock_open.assert_called_once_with(mock_absolute_path, "wb")
    mock_file.__enter__().write.assert_called_once_with(mock_content)
    mock_response.iter_content.assert_called_once_with(chunk_size=1024)


def test_sharepointgraphql_download_file_failure(mock_object, monkeypatch):
    # Arrange
    test_url = "https://example.com/test.txt"
    test_output_path = "test/output/file.txt"
    mock_absolute_path = "/absolute/path/to/test/output/file.txt"

    # Mock the setup_local_directory method
    monkeypatch.setattr(
        mock_object,
        "_setup_local_directory",
        MagicMock(return_value=mock_absolute_path)
    )

    class MockResponse:
        def __init__(self, json_data, status_code=200):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return self.json_data

        def raise_for_status(self):
            if self.status_code != 200:
                raise requests.exceptions.HTTPError("HTTP Error")

    def mock_requests_get(*args, **kwargs):
        return MockResponse({"Error": "Resource not found."}, 404)

    # Mock requests.get to raise an exception
    monkeypatch.setattr(
        "requests.get",
        mock_requests_get
    )

    # Act & Assert
    with pytest.raises(TransactionError):
        mock_object.download_file(test_url, test_output_path)


def test_sharepointgraphql_download_file_by_relative_path_success(mock_object, monkeypatch):
    # Arrange
    remote_path = "Documents/test.txt"
    local_path = "local/test.txt"
    mock_download_url = "https://graph.microsoft.com/downloads/test.txt"

    class MockResponse:
        def __init__(self, json_data, status_code=200):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return self.json_data

        def raise_for_status(self):
            if self.status_code != 200:
                raise requests.exceptions.RequestException("HTTP Error")

    def mock_requests_get(*args, **kwargs):
        if args[0] == f"{SharePointGraphql.GRAPH_BASE_URL}/sites/{mock_object.site_id}/drive/root:/{remote_path}":
            return MockResponse({SharePointGraphql.DOWNLOAD_URL_KEY: mock_download_url})
        return MockResponse({})

    # Mock the requests.get method and download_file
    monkeypatch.setattr("requests.get", mock_requests_get)
    download_file_called = False

    # Mock the download_file method
    def mock_download_file(url, output_path):
        nonlocal download_file_called
        assert url == mock_download_url
        assert output_path == local_path
        download_file_called = True

    monkeypatch.setattr(mock_object, "download_file", mock_download_file)

    # Act
    result = mock_object.download_file_by_relative_path(remote_path, local_path)

    # Assert
    assert download_file_called


def test_sharepointgraphql_download_file_by_relative_path_missing_download_url(mock_object, monkeypatch):
    # Arrange
    remote_path = "Documents/test.txt"
    local_path = "local/test.txt"

    class MockResponse:
        def json(self):
            return {}

        def raise_for_status(self):
            pass

    monkeypatch.setattr("requests.get", lambda *args, **kwargs: MockResponse())

    # Act & Assert
    with pytest.raises(KeyError, match="Download URL not found in response"):
        mock_object.download_file_by_relative_path(remote_path, local_path)


def test_sharepointgraphql_download_file_by_relative_path_http_error(mock_object, monkeypatch):
    # Arrange
    remote_path = "Documents/test.txt"
    local_path = "local/test.txt"

    class MockResponse:
        def raise_for_status(self):
            raise requests.exceptions.RequestException("HTTP Error")

    monkeypatch.setattr("requests.get", lambda *args, **kwargs: MockResponse())

    # Act & Assert
    with pytest.raises(requests.exceptions.RequestException, match="HTTP Error"):
        mock_object.download_file_by_relative_path(remote_path, local_path)


def test_delete_file_by_relative_path(mock_object, monkeypatch):
    # Arrange
    remote_path = "Documents/test.txt"
    mock_response = {
        "id": "mock_file_id"
    }

    def mock_delete(url, headers):
        return MockResponse(mock_response, 200)

    monkeypatch.setattr("requests.delete", mock_delete)

    # Act
    result = mock_object.delete_file_by_relative_path(remote_path)

    # Assert
    assert result is None


def test_delete_file_by_relative_path_failure(mock_object, monkeypatch):
    # Arrange
    remote_path = "Documents/test.txt"
    mock_response = {
        "id": "mock_file_id"
    }

    def mock_delete(url, headers):
        return MockResponseTransactionError(mock_response, 404)

    monkeypatch.setattr("requests.delete", mock_delete)

    # Act & Assert
    with pytest.raises(TransactionError):
        mock_object.delete_file_by_relative_path(remote_path)


def test__execute_move_request(mock_object, monkeypatch):
    # Arrange
    source_path = "Documents/test.txt"
    destination_path = "Documents/Folder/test.txt"
    mock_response = {
        "id": "mock_file_id"
    }

    def mock_patch(url, headers, stream, json):
        return MockResponse(mock_response, 200)

    monkeypatch.setattr("requests.patch", mock_patch)

    # Act
    result = mock_object._execute_move_request(source_path, destination_path)

    # Assert
    assert result is None


def test__execute_move_request_failure(mock_object, monkeypatch):
    # Arrange
    source_path = "Documents/test.txt"
    destination_path = "Documents/Folder/test.txt"
    mock_response = {
        "id": "mock_file_id"
    }

    def mock_patch(url, headers, stream, json):
        return MockResponseTransactionError(mock_response, 400)

    monkeypatch.setattr("requests.patch", mock_patch)

    # Act & Assert
    with pytest.raises(requests.exceptions.HTTPError):
        mock_object._execute_move_request(source_path, destination_path)


def test__build_move_destination_payload(mock_object):
    # Arrange
    file_name = "test.txt"
    destination_path = f"Documents/{file_name}"
    expected_destination_path = destination_path.split("/")[0]
    expected_payload = {
        "parentReference": {
            "path": f"drives/{mock_object.documents_id}/root:/{expected_destination_path}"},
        "name": file_name
    }

    # Act
    payload = mock_object._build_move_destination_payload(destination_path)

    # Assert
    assert payload == expected_payload


def test_move_file_success(mock_object, monkeypatch):
    # Arrange
    source_path = "Documents/test.txt"
    destination_path = "Documents/Folder/test.txt"
    expected_payload = {
        "parentReference": {
            "path": f"drives/{mock_object.documents_id}/root:/Documents/Folder"
        },
        "name": "test.txt"
    }

    def mock_patch(url, headers, json, stream):
        assert url == mock_object._build_graph_url(source_path)
        assert headers == mock_object.headers
        assert json == expected_payload
        return MockResponse({"id": "mock_file_id"}, 200)

    monkeypatch.setattr("requests.patch", mock_patch)

    # Act
    result = mock_object.move_file(source_path, destination_path)

    # Assert
    assert result is None


def test_move_file_failure(mock_object, monkeypatch):
    # Arrange
    source_path = "Documents/test.txt"
    destination_path = "Documents/Folder/test.txt"
    error_message = "Failed to move file"

    def mock_patch(*args, **kwargs):
        raise requests.exceptions.HTTPError(error_message)

    monkeypatch.setattr("requests.patch", mock_patch)

    # Act & Assert
    with pytest.raises(TransactionError, match=f"Error moving file: {error_message}"):
        mock_object.move_file(source_path, destination_path)


def test_upload_file_by_relative_path_success(mock_object, monkeypatch):
    # Arrange
    remote_path = "Documents/test.txt"
    local_path = "local/test.txt"
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    def mock_put(url, headers, stream, data):
        assert url == mock_object._build_graph_url(remote_path, "content")
        assert headers == mock_object.headers
        assert stream is True
        assert data == b"mock file content"
        return mock_response

    monkeypatch.setattr("requests.put", mock_put)

    mock_open = MagicMock()
    mock_open.return_value.__enter__.return_value.read.return_value = b"mock file content"
    monkeypatch.setattr("builtins.open", mock_open)

    # Act
    mock_object.upload_file_by_relative_path(remote_path, local_path)

    # Assert
    mock_response.raise_for_status.assert_called_once()


def test_upload_file_by_relative_path_failure(mock_object, monkeypatch):
    # Arrange
    remote_path = "Documents/test.txt"
    local_path = "local/test.txt"

    def mock_put(url, headers, stream, data):
        raise requests.exceptions.HTTPError("Mocked upload error")

    monkeypatch.setattr("requests.put", mock_put)

    mock_open = MagicMock()
    mock_open.return_value.__enter__.return_value.read.return_value = b"mock file content"
    monkeypatch.setattr("builtins.open", mock_open)

    # Act & Assert
    with pytest.raises(requests.exceptions.HTTPError, match="Mocked upload error"):
        mock_object.upload_file_by_relative_path(remote_path, local_path)


def test_get_token(mock_client, mock_object_for_testing_token, monkeypatch):
    # Arrange
    mock_access_token = "mock_access_token"

    # class MockConfidentialClientApplication:
    #     def __init__(self, authority, client_id, client_credential):
    #         pass
    #
    #     def acquire_token_for_client(self, scopes):
    #         return {"access_token": mock_access_token}
    #
    # monkeypatch.setattr("msal.ConfidentialClientApplication", MockConfidentialClientApplication)

    # Act
    token = mock_object_for_testing_token._get_token(mock_client['client_id'], mock_client['client_secret'],
                                                     mock_client['tenant_id'])
    # Assert
    assert token == mock_access_token
