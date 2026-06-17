import abc

class BaseProvider(abc.ABC):
    @abc.abstractmethod
    async def download(self, url: str, download_dir: str, progress_callback=None) -> dict:
        """
        Downloads a video from the given URL and returns its metadata.
        
        Parameters:
          - url: The media URL to download.
          - download_dir: Directory where the temporary files will be saved.
          - progress_callback: Async/thread-safe callback called with status strings.
          
        Returns:
          A dict containing:
            - 'file_path': Absolute path to the downloaded video file.
            - 'duration': Duration of the video in seconds (int or None).
            - 'width': Width of the video (int or None).
            - 'height': Height of the video (int or None).
            - 'title': Title/caption of the video (str or None).
        """
        pass
