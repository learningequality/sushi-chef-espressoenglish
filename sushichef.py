#!/usr/bin/env python
import os
import sys
from ricecooker.utils import downloader, html_writer
from ricecooker.chefs import SushiChef
from ricecooker.classes import nodes, files, questions
from ricecooker.classes.licenses import get_license
from ricecooker.config import LOGGER              # Use LOGGER to print messages
from ricecooker.exceptions import raise_for_invalid_channel
from le_utils.constants import exercises, content_kinds, file_formats, format_presets, languages, licenses

# Run constants
################################################################################
CHANNEL_NAME = "Espresso English"                       # Name of channel
CHANNEL_SOURCE_ID = "sushi-chef-espresso-english-en"    # Channel's unique id
CHANNEL_DOMAIN = "learningequality.org"                 # Who is providing the content
CHANNEL_LANGUAGE = "en"                                 # Language of channel
# Description of the channel
CHANNEL_DESCRIPTION = "Espresso English is a YouTube channel that features Shayna, an experienced ESL teacher who provides learners with English lessons in vocabulary, grammar and conversational English as well."
CHANNEL_THUMBNAIL = "thumbnail.jpg"                     # Local path or url to image file (optional)

# Additional constants
################################################################################
YOUTUBE_CHANNEL_ID = 'UCKjOCfT-w4ePd98Y_g8gTqg'
SUBTITLE_LANGUAGES = ['ar']

# The chef subclass
################################################################################
class YouTubeChannelChef(SushiChef):
    """
    This class uploads the Espresso English channel to Kolibri Studio.
    Your command line script should call the `main` method as the entry point,
    which performs the following steps:
      - Parse command line arguments and options (run `./sushichef.py -h` for details)
      - Call the `SushiChef.run` method which in turn calls `pre_run` (optional)
        and then the ricecooker function `uploadchannel` which in turn calls this
        class' `get_channel` method to get channel info, then `construct_channel`
        to build the contentnode tree.
    For more info, see https://github.com/learningequality/ricecooker/tree/master/docs
    """
    channel_info = {                                   # Channel Metadata
        'CHANNEL_SOURCE_DOMAIN': CHANNEL_DOMAIN,       # Who is providing the content
        'CHANNEL_SOURCE_ID': CHANNEL_SOURCE_ID,        # Channel's unique id
        'CHANNEL_TITLE': CHANNEL_NAME,                 # Name of channel
        'CHANNEL_LANGUAGE': CHANNEL_LANGUAGE,          # Language of channel
        'CHANNEL_THUMBNAIL': CHANNEL_THUMBNAIL,        # Local path or url to image file (optional)
        'CHANNEL_DESCRIPTION': CHANNEL_DESCRIPTION,    # Description of the channel (optional)
    }

    def playlists_list_by_youtube_channel_id(self, client, **kwargs):
        # See full sample for function
        response = client.playlists().list(
            **kwargs
        ).execute()

        return response

    # Your chef subclass can ovverdie/extend the following method:
    # get_channel: to create ChannelNode manually instead of using channel_info
    # pre_run: to perform preliminary tasks, e.g., crawling and scraping website
    # __init__: if need to customize functionality or add command line arguments

    def construct_channel(self, *args, **kwargs):
        """
        Creates ChannelNode and build topic tree
        Args:
          - args: arguments passed in during upload_channel (currently None)
          - kwargs: extra argumens and options not handled by `uploadchannel`.
            For example, add the command line option   lang="fr"  and the string
            "fr" will be passed along to `construct_channel` as kwargs['lang'].
        Returns: ChannelNode
        """
        channel = self.get_channel(*args, **kwargs)  # Create ChannelNode from data in self.channel_info
        
        from apiclient.discovery import build
        # instantiate a YouTube Data API v3 client
        youtube = build('youtube', 'v3', developerKey=kwargs['--youtube-api-token'])
        playlists = youtube.playlists().list( # list all of the YouTube channel's playlists
            part='snippet',
            channelId=YOUTUBE_CHANNEL_ID,
            maxResults=50
        ).execute()['items']

        for playlist in playlists:
            topic = nodes.TopicNode(title=playlist['snippet']['title'], source_id=playlist['id'])
            first_page = True
            next_page_token = None
            playlist_request_kwargs = {
                'part': 'contentDetails',
                'maxResults': 50,
                'playlistId': playlist['id'],
            }

            while first_page or next_page_token:
                first_page = False # we're visiting the first page now!
                playlist_info = youtube.playlistItems().list(**playlist_request_kwargs).execute()
                playlist_items = playlist_info['items']

                video_ids = [vid['contentDetails']['videoId'] for vid in playlist_items]
                videos = youtube.videos().list(
                    part='status,snippet',
                    id=','.join(video_ids)
                ).execute()['items']

                for video in videos:
                    if video['status']['license'] == 'creativeCommon':
                        try:
                            video_node = nodes.VideoNode(
                                source_id=video['id'],
                                title=video['snippet']['title'],
                                language=CHANNEL_LANGUAGE,
                                license=get_license(licenses.CC_BY, copyright_holder='Espresso English'),
                                thumbnail=video['snippet']['thumbnails']['high']['url'],
                                files=[
                                    files.YouTubeVideoFile(video['id']),
                                ]
                            )

                            topic.add_child(video_node)
                            
                            # Get subtitles for languages designated in SUBTITLE_LANGUAGES
                            for lang_code in SUBTITLE_LANGUAGES:
                                if files.is_youtube_subtitle_file_supported_language(lang_code):
                                    video_node.add_file(
                                        files.YouTubeSubtitleFile(
                                            youtube_id=video['id'],
                                            language=lang_code
                                        )
                                    )
                                else:
                                    print('Unsupported subtitle language code:', lang_code)

                        except Exception as e:
                            raise e
                
                # set up the next page, if there is one
                next_page_token = playlist_info.get('nextPageToken')
                if next_page_token:
                    playlist_request_kwargs['pageToken'] = next_page_token
                else:
                    try:
                        del playlist_request_kwargs['pageToken']
                    except Exception as e:
                        pass

            channel.add_child(topic)

        raise_for_invalid_channel(channel)  # Check for errors in channel construction

        return channel



# CLI
################################################################################
if __name__ == '__main__':

    # This code runs when sushichef.py is called from the command line
    chef = YouTubeChannelChef()
    chef.main()
