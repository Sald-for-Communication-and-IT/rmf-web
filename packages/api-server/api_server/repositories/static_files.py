import logging
import os


class StaticFilesRepository:
    def __init__(
        self,
        base_url: str,
        directory: str,
        logger: logging.Logger = None,
    ):
        """
        :param base_url: base url that static files are served from. When running behind a proxy,
        this should be the url of the proxy.
        :param directory: location to write the files to.
        This should be the same directory that a static files server is serving from.
        """
        self.base_url = base_url
        self.directory = directory
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    def add_file(self, data: bytes, path: str) -> str:
        """
        Parameters:
            data:
            path: relative path to save the file to
        Returns:
            the url path of the new file
        """
        filepath = f"{self.directory}/{path}"
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "bw") as f:
            f.write(data)
        self.logger.info(f'saved new file "{filepath}"')
        urlpath = f"{self.base_url}/{path}"
        return urlpath
