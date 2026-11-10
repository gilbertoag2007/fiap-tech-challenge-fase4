import argparse
import json
import time
from itertools import zip_longest

import requests

from .config import root_path, digest, write_json
from .dataset import prepare, load_catalog
from .pose import extract_pose
from .training import train, current_experiment


def main():
    parser = argparse.ArgumentParser(description='Preparação e análise REHAB24-6 Ex1–Ex4')
    parser.add_argument('command', choices=['prepare','weights','extract','train','evaluate'])
    parser.add_argument('--root',type=__import__('pathlib').Path,default=root_path())
    parser.add_argument('--video-id')
    parser.add_argument('--device',choices=['cpu','mps','cuda:0'],help='Persiste a configuração para extração e API.')
    parser.add_argument('--batch',type=int,default=8)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.device:
        if args.batch < 1 or args.batch > 32:
            parser.error('batch deve estar entre 1 e 32.')
        write_json(root/'runtime.json',{'device':args.device,'batch':args.batch})
    started = time.monotonic()
    if args.command == 'prepare':
        catalog = prepare(root)
        print(json.dumps({'videos':len(catalog['videos']),'exercises':catalog['exercises']},ensure_ascii=False))
    elif args.command == 'weights':
        target = root/'models/yolov8n-pose.pt'
        target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():
            with requests.get('https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n-pose.pt',stream=True,timeout=(30,120)) as response:
                response.raise_for_status()
                temporary = target.with_suffix('.part')
                with temporary.open('wb') as output:
                    for block in response.iter_content(1024*1024):
                        output.write(block)
                temporary.replace(target)
        write_json(target.with_suffix('.json'),{'source':'ultralytics/assets/v8.3.0','sha256':digest(target)})
        print(f'Pesos preparados: {target.name}')
    elif args.command == 'extract':
        videos = load_catalog(root)['videos']
        if args.video_id:
            videos = [v for v in videos if v['id']==args.video_id]
            if not videos:
                raise ValueError('Vídeo não encontrado no catálogo.')
        else:
            buckets = [[v for v in videos if v['exercise_id']==exercise] for exercise in (1,2,3,4)]
            videos = [video for group in zip_longest(*buckets) for video in group if video is not None]
        for index,video in enumerate(videos):
            print(f"[{index+1}/{len(videos)}] {video['recording_id']} câmera {video['camera']}",flush=True)
            last_print=[-300]
            def progress(n,total):
                if n-last_print[0]>=300 or n==total:
                    print(f'  {n}/{total} frames',flush=True)
                    last_print[0]=n
            extract_pose(root,video,progress)
    elif args.command == 'train':
        result = train(root)
        print(json.dumps({key:value['metrics'] for key,value in result['exercises'].items()},ensure_ascii=False,indent=2))
    else:
        result = current_experiment(root)
        print(json.dumps({key:{'metrics':value['metrics'],'baseline':value['baseline'],'above_baseline':value['above_baseline']} for key,value in result['exercises'].items()},ensure_ascii=False,indent=2))
    print(f'Duração: {time.monotonic()-started:.1f}s',flush=True)


if __name__ == '__main__':
    main()
