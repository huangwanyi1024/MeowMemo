"""Contract/error tests using a mocked OpenAI response. No paid API requests."""
import json
import os
import unittest
from unittest.mock import patch, Mock
import requests
from pydantic import ValidationError
import caption_service as service


class CaptionTests(unittest.TestCase):
    def setUp(self):
        service._recent_calls.clear()
        self.env = patch.dict(os.environ, {'OPENAI_API_KEY': 'test-only-never-real',
                              'MEOWMEMO_CLOUD_CAPTIONS': '1', 'MEOWMEMO_CAPTION_MODEL': 'gpt-6-luna',
                              'MEOWMEMO_CAPTION_PROVIDER': 'openai'})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.data = service.CaptionInput(catId='orange', context='food', personality='clingy',
                         ownerStyle='academic', catDescription='A talkative orange cat with white socks.',
                         ownerDescription='A grad student who lifts.', memoryTitle='Late-night study buddy',
                         memoryNote='I was finishing an assignment.', language='en')

    def test_no_key_no_request(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': ''}), patch.object(service.requests, 'post') as post:
            self.assertFalse(service.configuration_status()['available'])
            with self.assertRaises(service.CaptionError) as cm:
                service.generate_caption(self.data)
            self.assertEqual(cm.exception.code, 'caption_not_configured')
            post.assert_not_called()

    def test_key_alone_does_not_enable_cloud(self):
        with patch.dict(os.environ, {'MEOWMEMO_CLOUD_CAPTIONS': '0'}):
            self.assertFalse(service.configuration_status()['available'])

    def test_personalization_and_provenance(self):
        response = Mock(status_code=200)
        response.json.return_value = {'status': 'completed', 'output': [
            {'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps({'text': 'Could my fish proposal get an early review?'})}]}]}
        with patch.object(service.requests, 'post', return_value=response) as post:
            result = service.generate_caption(self.data)
            url = post.call_args.args[0]
            payload = post.call_args.kwargs['json']
            self.assertEqual(url, 'https://api.openai.com/v1/responses')
            self.assertFalse(payload['store'])
            self.assertEqual(payload['reasoning']['effort'], 'none')
            self.assertEqual(payload['text']['format']['type'], 'json_schema')
            sent = json.loads(payload['input'][1]['content'])
            self.assertEqual(sent['catDescription'], self.data.catDescription)
            self.assertEqual(sent['ownerDescription'], self.data.ownerDescription)
            self.assertEqual(sent['memoryNote'], self.data.memoryNote)
            self.assertNotIn('audio', sent)
            self.assertNotIn('inferenceStatus', sent)
            self.assertEqual(result['source'], 'ai-copy')
            self.assertTrue(result['forFun'])
            self.assertEqual(result['basedOn'], 'owner-observation')
            self.assertEqual(result['personalization']['memoryTitle'], self.data.memoryTitle)
            self.assertNotIn('test-only-never-real', str(service.configuration_status()))

    def test_unknown_stays_unknown(self):
        data = self.data.model_copy(update={'context': 'unknown', 'memoryNote': 'Maybe hungry?'})
        self.assertEqual(data.context, 'unknown')
        self.assertIn('If unknown, stay genuinely open-ended', service.SYSTEM_PROMPT)

    def test_refusal_incomplete_and_bad_json(self):
        for body in [{'status': 'incomplete'}, {'status': 'completed', 'output': []},
                     {'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': 'not JSON'}]}]}]:
            response = Mock(status_code=200); response.json.return_value = body
            with patch.object(service.requests, 'post', return_value=response):
                with self.assertRaises(service.CaptionError):
                    service.generate_caption(self.data)

    def test_errors_hide_provider_secrets(self):
        response = Mock(status_code=401, text='upstream secret should never be reflected')
        with patch.object(service.requests, 'post', return_value=response):
            with self.assertRaises(service.CaptionError) as cm:
                service.generate_caption(self.data)
            self.assertNotIn('upstream secret', cm.exception.message)
        with patch.object(service.requests, 'post', side_effect=requests.Timeout('secret internal data')):
            with self.assertRaises(service.CaptionError) as cm:
                service.generate_caption(self.data)
            self.assertNotIn('secret internal data', cm.exception.message)

    def test_reject_media_model_override_and_oversized_notes(self):
        for extra in [{'audio': 'base64'}, {'model': 'unapproved-model'}, {'memoryNote': 'x' * 1501},
                      {'contextSource': 'model'}]:
            with self.assertRaises(ValidationError):
                service.CaptionInput(**{**self.data.model_dump(), **extra})

    def test_local_provider_uses_only_loopback_without_a_key(self):
        tags = Mock(ok=True); tags.json.return_value = {'models': [{'name': 'qwen3.5:4b'}]}
        response = Mock(); response.json.return_value = {'done': True, 'done_reason': 'stop',
                            'message': {'content': '{"text":"Could my fish proposal get an early review?"}'}}
        with patch.dict(os.environ, {'MEOWMEMO_CAPTION_PROVIDER': 'ollama', 'OPENAI_API_KEY': '',
                                     'MEOWMEMO_LOCAL_MODEL': 'qwen3.5:4b'}), \
             patch.object(service.requests, 'get', return_value=tags), \
             patch.object(service.requests, 'post', return_value=response) as post:
            output = service.generate_caption(self.data)
            self.assertEqual(post.call_args.args[0], 'http://127.0.0.1:11434/api/chat')
            self.assertNotIn('headers', post.call_args.kwargs)
            self.assertFalse(post.call_args.kwargs['json']['think'])
            self.assertTrue(output['localOnly'])
            self.assertTrue(output['generatorVersion'].startswith('ollama:'))

    def test_current_story_and_tags_survive_unknown(self):
        data = self.data.model_copy(update={'context': 'unknown', 'memoryTitle': 'First peaceful moment',
                    'memoryNote': 'Two cats sat peacefully together waiting for dried fish.',
                    'memoryTags': ['Together', 'FishTreats'], 'participantNames': ['Miso', 'Nori'],
                    'previousText': 'An unrelated study session.'})
        sent = service.local_story_data(data)
        self.assertEqual(sent['current_memory']['memoryNote'], data.memoryNote)
        self.assertEqual(sent['current_memory']['memoryTags'], data.memoryTags)
        self.assertEqual(sent['owner_confirmed_context'], 'unknown')
        self.assertEqual(sent['cats_in_this_moment'], 2)
        self.assertNotIn('study session', str(sent))
        self.assertNotIn('background_voice_only', sent)
        result = service.caption_result(data, 'Our first fish-treat truce.', 'test', True)
        self.assertEqual(result['personalization']['memoryTags'], data.memoryTags)

    def test_unrelated_study_topic_is_rejected_without_replacing_caption(self):
        data = self.data.model_copy(update={'memoryTitle': 'Peaceful together',
                    'memoryNote': 'Two cats waited for fish.', 'memoryTags': ['Together']})
        with self.assertRaises(service.CaptionError) as error:
            service.validate_grounding(data, 'A quiet study session.')
        self.assertEqual(error.exception.code, 'caption_ungrounded')
        service.validate_grounding(data, 'Our little fish-treat truce.')
        service.validate_grounding(self.data, 'Your assignment can wait for a fish break.')

    def test_one_local_grounding_rewrite_only(self):
        def response(text):
            result = Mock()
            result.json.return_value = {'done': True, 'done_reason': 'stop',
                                       'message': {'content': json.dumps({'text': text})}}
            return result
        data = self.data.model_copy(update={'context': 'unknown', 'memoryTitle': 'Peaceful together',
                  'memoryNote': 'Two cats got along for the first time.', 'memoryTags': ['Together']})
        config = {'model': 'qwen3.5:4b'}
        with patch.object(service.requests, 'post', side_effect=[response('A quiet study session.'), response('Our first little truce.')]) as post:
            result = service.generate_local_caption(data, config)
            self.assertEqual(post.call_count, 2)
            self.assertTrue(result['groundingRepair'])
            self.assertEqual(result['text'], 'Our first little truce.')
        with patch.object(service.requests, 'post', return_value=response('A quiet study session.')) as post:
            with self.assertRaises(service.CaptionError):
                service.generate_local_caption(data, config)
            self.assertEqual(post.call_count, 2)

    def test_bounded_text_only_tags_and_cast(self):
        for extra in [{'memoryTags': ['x'] * 21}, {'memoryTags': ['x' * 51]},
                      {'participantNames': ['x'] * 6}, {'catName': 'x' * 51}]:
            with self.assertRaises(ValidationError):
                service.CaptionInput(**{**self.data.model_dump(), **extra})

    def test_five_choices_identity_voice_and_deduplication(self):
        data = self.data.model_copy(update={'count': 5, 'memoryNote': 'Two cats wait for fish.',
            'memoryTitle': 'Treat truce', 'catName': 'Nori', 'memoryTags': ['Together'],
            'participantDetails': ['Nori: younger sister, goofy', 'Miso: older sister, clingy'],
            'avoidTexts': ['Old joke']})
        sent = service.choice_story_data(data)
        self.assertEqual(sent['selectedCat']['name'], 'Nori')
        self.assertEqual(sent['selectedCat']['profile'], data.catDescription)
        self.assertEqual(sent['expressionStyle'], 'academic')
        self.assertEqual(sent['avoidTexts'], ['Old joke'])
        self.assertEqual(sent['participantProfiles'], data.participantDetails)
        options = [{'angle': 'A', 'text': f'Fish treaty version {i}.'} for i in range(5)]
        self.assertEqual(len(service.parse_choices(json.dumps({'options': options}), data)), 5)
        for invalid in [options[:4], options+[options[0]], [options[0]]*5]:
            with self.assertRaises(ValueError):
                service.parse_choices(json.dumps({'options': invalid}), data)
        options[2]['text'] = 'A quiet study session.'
        with self.assertRaises(service.CaptionError):
            service.parse_choices(json.dumps({'options': options}), data)

    def test_cloud_batch_has_one_billable_call_and_no_retry(self):
        data = self.data.model_copy(update={'count': 5})
        body = {'options': [{'angle': 'A', 'text': f'Fish proposal number {i}.'} for i in range(5)]}
        r = Mock(status_code=200)
        r.json.return_value = {'status': 'completed', 'output': [{'type': 'message', 'content': [
            {'type': 'output_text', 'text': json.dumps(body)}]}]}
        with patch.object(service.requests, 'post', return_value=r) as post:
            result = service.generate_caption_choices(data, {'provider': 'OpenAI', 'model': 'gpt-6-luna'})
            self.assertEqual(post.call_count, 1)
            self.assertEqual(len(result['options']), 5)
            self.assertFalse(result['localOnly'])
            self.assertFalse(post.call_args.kwargs['json']['store'])
        r.json.return_value = {'status': 'incomplete'}
        with patch.object(service.requests, 'post', return_value=r) as post:
            with self.assertRaises(service.CaptionError):
                service.generate_caption_choices(data, {'provider': 'OpenAI', 'model': 'gpt-6-luna'})
            self.assertEqual(post.call_count, 1)

    def test_local_batch_one_call_and_bounded_repair(self):
        data = self.data.model_copy(update={'count': 5})
        valid = {'options': [{'angle': 'A', 'text': f'Fish proposal number {i}.'} for i in range(5)]}
        def response(body):
            r = Mock(); r.json.return_value = {'done': True, 'message': {'content': json.dumps(body)}}
            return r
        with patch.object(service.requests, 'post', return_value=response(valid)) as post:
            result = service.generate_caption_choices(data, {'provider': 'Ollama', 'model': 'qwen3.5:4b'})
            self.assertEqual(post.call_count, 1)
            self.assertEqual(len(result['options']), 5)
            self.assertTrue(result['localOnly'])
        with patch.object(service.requests, 'post', side_effect=[response({'options': []}), response(valid)]) as post:
            result = service.generate_caption_choices(data, {'provider': 'Ollama', 'model': 'qwen3.5:4b'})
            self.assertEqual(post.call_count, 2)
            self.assertTrue(result['groundingRepair'])
        with patch.object(service.requests, 'post', return_value=response({'options': []})) as post:
            with self.assertRaises(service.CaptionError):
                service.generate_caption_choices(data, {'provider': 'Ollama', 'model': 'qwen3.5:4b'})
            self.assertEqual(post.call_count, 2)


    def test_local_down_never_falls_back_to_cloud(self):
        with patch.dict(os.environ, {'MEOWMEMO_CAPTION_PROVIDER': 'ollama'}), \
             patch.object(service.requests, 'get', side_effect=requests.ConnectionError), \
             patch.object(service.requests, 'post') as post:
            with self.assertRaises(service.CaptionError):
                service.generate_caption(self.data)
            post.assert_not_called()


if __name__ == '__main__':
    unittest.main()
