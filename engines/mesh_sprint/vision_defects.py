"""Image-based structural defect detector for *rendered real GLBs*.

This is bounded OpenCV computer vision, not pretrained VLM inference.
If source art is provided it computes normalized silhouette overlap; without it,
report style-contract evidence only and never grant source-image approval.
"""
from pathlib import Path
import numpy as np
import cv2
from PIL import Image


def mask_from_render(image):
    rgb=np.asarray(image.convert('RGB'),dtype=np.int16)
    bg=np.array([241,242,241],dtype=np.int16)
    # The current renderer background is flat, so a small tolerance suffices.
    return np.max(np.abs(rgb-bg),axis=2)>18


def metrics(image):
    rgb=np.asarray(image.convert('RGB'),dtype=np.uint8)
    mask=mask_from_render(image)
    if mask.sum()<60:return {'foreground_fraction':0,'edge_density':0,'bbox_width_ratio':0,
      'bbox_height_ratio':0,'green_fraction':0,'brown_fraction':0,'metal_fraction':0,'components':0}
    m=mask.astype('uint8')*255
    n,labels,stats,_=cv2.connectedComponentsWithStats(m,8)
    comps=int(np.sum(stats[1:,cv2.CC_STAT_AREA]>30)) if n>1 else 0
    ys,xs=np.nonzero(mask);width=float(xs.max()-xs.min()+1)/mask.shape[1];height=float(ys.max()-ys.min()+1)/mask.shape[0]
    roi=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY)
    # edge density is relative to visible pixels; avoids background dominating.
    edge=cv2.Canny(roi,60,130)>0
    f=rgb.astype(float);r,g,b=f[:,:,0],f[:,:,1],f[:,:,2]
    green=(g>r*1.09)&(g>b*1.05)&(g>37)
    brown=(r>g*1.25)&(g>b*1.12)&(r>55)
    metal=(np.abs(r-g)<24)&(np.abs(g-b)<28)&(r>65)&(r<205)
    denom=max(1,int(mask.sum()))
    return {'foreground_fraction':round(float(mask.mean()),5),
      'edge_density':round(float((edge&mask).sum()/denom),5),
      'bbox_width_ratio':round(width,5),'bbox_height_ratio':round(height,5),
      'green_fraction':round(float((green&mask).sum()/denom),5),
      'brown_fraction':round(float((brown&mask).sum()/denom),5),
      'metal_fraction':round(float((metal&mask).sum()/denom),5),'components':comps}


def normalized_iou(candidate,reference,size=256):
    """Measure segmentation IoU after independently cropping/normalizing art silhouettes.

    Does not prove cross-view alignment; source provenance and view must be reviewed.
    """
    def crop(im):
        if im.mode=='RGBA':m=np.asarray(im)[:,:,3]>12
        else:m=mask_from_render(im)
        yy,xx=np.nonzero(m)
        if not len(xx):raise ValueError('Reference/candidate has no foreground')
        crop=m[yy.min():yy.max()+1,xx.min():xx.max()+1].astype('uint8')
        h,w=crop.shape;scale=(size-24)/max(w,h)
        rs=cv2.resize(crop,(max(1,int(round(w*scale))),max(1,int(round(h*scale)))),interpolation=cv2.INTER_NEAREST)
        canvas=np.zeros((size,size),dtype=np.uint8);rh,rw=rs.shape;canvas[(size-rh)//2:(size-rh)//2+rh,(size-rw)//2:(size-rw)//2+rw]=rs
        return canvas>0
    a=crop(candidate);b=crop(reference)
    return round(float((a&b).sum()/max(1,(a|b).sum())),5)


def detect(image,contract,reference_path=None):
    stat=metrics(image);targets=contract['visual_targets'];failures=[]
    for field,minimum in targets.items():
        k={'bbox_width_ratio_max':'bbox_width_ratio','foreground_min':'foreground_fraction','landmark_green_min':'green_fraction',
           'landmark_brown_min':'brown_fraction','landmark_metal_min':'metal_fraction',
           'edge_density_min':'edge_density'}[field]
        if field.endswith('_max') and stat[k]>minimum:
            failures.append({'code':'excess_'+k,'actual':stat[k],'maximum':minimum})
        elif field.endswith('_min') and stat[k]<minimum:
            failures.append({'code':'low_'+k,'actual':stat[k],'minimum':minimum})
    if stat['components']>1:
        failures.append({'code':'disconnected_screen_islands','components':stat['components'],'allowed':1})
    iou=None
    if reference_path is not None:
        reference=Image.open(reference_path)
        iou=normalized_iou(image,reference)
        if iou<0.66:failures.append({'code':'reference_silhouette_low','iou':iou,'minimum':.66})
    return {'metrics':stat,'defects':failures,'structural_screen_pass':not failures,
      'reference_iou':iou,'reference_fidelity_state':'UNVERIFIED_NO_REFERENCE' if iou is None else 'SILHOUETTE_HEURISTIC_ONLY',
      'golden_approved':False}
