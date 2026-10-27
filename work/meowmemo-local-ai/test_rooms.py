import base64
import io
import json
import unittest
from unittest.mock import patch,Mock
from PIL import Image
import room_service as service

class RoomTests(unittest.TestCase):
    def photo(self):
        out=io.BytesIO();Image.new('RGB',(1600,900),'beige').save(out,'JPEG');return out.getvalue()
    def test_photo_validation_and_resize(self):
        raw=base64.b64decode(service.prepare_image(self.photo()))
        with Image.open(io.BytesIO(raw)) as im:self.assertLessEqual(max(im.size),768);self.assertEqual(im.format,'JPEG')
        for raw in [b'not a photo',b'x'*(10*1024*1024+1)]:
            with self.assertRaises(service.RoomError):service.prepare_image(raw)
    def test_bounded_recognized_furniture(self):
        result=service.normalize_room({'roomType':'living','objects':[{'kind':'sofa','x':-2,'y':20,'size':8},{'kind':'vacuum','x':.5,'y':.5},{'kind':'tree','x':float('nan'),'y':.5},{'kind':'window','x':.5,'y':.1,'size':1}]})
        self.assertEqual(len(result['objects']),2)
        self.assertEqual(result['objects'][0]['x'],12)
        self.assertEqual(result['objects'][0]['size'],1.4)
        self.assertLessEqual(result['objects'][1]['y'],48)
        self.assertEqual(result['source'],'local-vision')
        with self.assertRaises(service.RoomError):service.normalize_room({'objects':[]})
    def test_cloud_configuration_never_sends_photo(self):
        with patch.object(service,'configuration_status',return_value={'available':True,'localOnly':False,'model':'cloud'}),patch.object(service.requests,'post') as post:
            self.assertFalse(service.room_status()['available']);post.assert_not_called()
    def test_capability_must_include_vision(self):
        r=Mock(ok=True);r.json.return_value={'capabilities':['completion']}
        with patch.object(service,'configuration_status',return_value={'available':True,'localOnly':True,'model':'qwen3.5:4b'}),patch.object(service.requests,'post',return_value=r):
            self.assertFalse(service.room_status()['available'])
    def test_photo_request_loopback_and_failure_does_not_fabricate_layout(self):
        response=Mock();response.json.return_value={'done':True,'message':{'content':json.dumps({'roomType':'bedroom','objects':[{'kind':'bed','x':.5,'y':.8,'size':1}]})}}
        with patch.object(service,'room_status',return_value={'available':True,'model':'qwen3.5:4b'}),patch.object(service.requests,'post',return_value=response) as post:
            result=service.analyze_room(self.photo(),'bedroom')
            self.assertEqual(result['type'],'bedroom');self.assertEqual(post.call_count,1)
            self.assertEqual(post.call_args.args[0],'http://127.0.0.1:11434/api/chat')
            self.assertTrue(post.call_args.kwargs['json']['messages'][1]['images'])
            self.assertNotIn('photo',result)
            response.json.return_value={'done':False}
            with self.assertRaises(service.RoomError):service.analyze_room(self.photo())
    def test_busy_lock_and_release(self):
        lock=Mock();lock.acquire.return_value=False
        with patch.object(service,'room_status',return_value={'available':True,'model':'qwen3.5:4b'}),patch.object(service,'_local_generation_lock',lock),patch.object(service.requests,'post') as post:
            with self.assertRaises(service.RoomError) as error:service.analyze_room(self.photo())
            self.assertEqual(error.exception.status,429);post.assert_not_called()
if __name__=='__main__':unittest.main()
