"""Shape-first geometry archetypes. Original procedural constructions, not asset copies.

Every family uses explicit three-dimensional surfaces instead of substituting a box
for any unidentified part.  Front is -Y, Z is up, units are metres.  The five
private operators below form a reusable construction grammar for later V2 recipes.
"""
from __future__ import annotations
import math
import numpy as np

TAU = 2 * math.pi


def _grid(builder, material, rings, closed=True, caps=True):
    """Create a lofted solid through ordered closed (XYZ) cross-section rings."""
    rings = np.asarray(rings, dtype=float)
    if rings.ndim != 3 or rings.shape[2] != 3 or len(rings) < 2 or rings.shape[1] < 3:
        raise ValueError('Invalid surface loft')
    rows, cols, _ = rings.shape
    faces = []
    end = cols if closed else cols - 1
    for k in range(rows - 1):
        for j in range(end):
            nxt = (j + 1) % cols
            a = k * cols + j
            b = k * cols + nxt
            c = (k + 1) * cols + j
            d = (k + 1) * cols + nxt
            faces.extend(((a, b, d), (a, d, c)))
    verts = rings.reshape((-1, 3)).tolist()
    if caps and closed:
        # Each end is capped by a separate center vertex.
        a = len(verts)
        verts.append(rings[0].mean(axis=0).tolist())
        b = len(verts)
        verts.append(rings[-1].mean(axis=0).tolist())
        for j in range(cols):
            k = (j + 1) % cols
            faces.extend(((a, j, k), (b, (rows - 1)*cols + k, (rows - 1)*cols + j)))
    builder.add(material, verts, faces)


def _surface(builder, material, grids):
    """Surface grid for annular patches / body skin, with no fake body-filling plate."""
    _grid(builder, material, grids, closed=True, caps=False)


def _smooth_sections(section_data, segments_per_span=3):
    """Centripetal-like bounded interpolation of authored silhouette control sections.

    Subdivision adds actual cross-section topology and removes the ring-to-ring
    planar faceting that made previous backpacks and torso armor look blocky.
    Z is linearly interpolated to preserve strict height ordering; only the
    width/depth/center coordinates receive a Catmull-Rom shape curve.
    """
    src=np.asarray(section_data,float)
    if len(src)<3 or segments_per_span<2:return src
    rows=[]
    for k in range(len(src)-1):
        prev=src[max(0,k-1)]
        a=src[k];b=src[k+1]
        nex=src[min(len(src)-1,k+2)]
        for j in range(segments_per_span):
            u=j/segments_per_span
            smooth=.5*(2*a+(-prev+b)*u+(2*prev-5*a+4*b-nex)*u*u+
                        (-prev+3*a-3*b+nex)*u*u*u)
            smooth[0]=a[0]*(1-u)+b[0]*u
            smooth[1:3]=np.maximum(smooth[1:3],.003)
            rows.append(smooth)
    rows.append(src[-1].copy())
    return np.asarray(rows)


def superloft(builder, material, sections, *, n=36, exponent=2.8, noise_seed=0, center_x=0.0):
    """Variable-width/depth superelliptic shell; top and bottom are capped.

    Sections: [z, half_width_x, half_depth_y, center_y].  Exponent 2 is round,
    3 is padded textile silhouette; profiles can taper independently at each Z.
    """
    dims=np.asarray(sections,dtype=float)
    if (dims.ndim!=2 or dims.shape[1]!=4 or not 2<=len(dims)<=64 or
        not 12<=n<=64 or not .9<=exponent<=5 or not np.isfinite(dims).all() or
        np.any(dims[:,1:3]<=0) or np.max(np.abs(dims))>50 or
        not np.all(np.diff(dims[:,0])>0) or
        not np.isfinite(center_x) or abs(center_x)>50):
        raise ValueError('Invalid physically bounded superloft profile')
    dims=_smooth_sections(dims,segments_per_span=3)
    theta = np.linspace(0, TAU, n, endpoint=False)
    def super_sin(t): return np.sign(np.sin(t))*np.abs(np.sin(t))**(2/exponent)
    def super_cos(t): return np.sign(np.cos(t))*np.abs(np.cos(t))**(2/exponent)
    cx, sy = super_cos(theta), super_sin(theta)
    phase=(int(noise_seed)%991)*TAU/991
    rows = []
    for index, (z, rx, ry, cy) in enumerate(sections):
        # Modest, deterministic cross-section irregularity: fabric tension, not crumpled polygons.
        flutter = (0.004 * np.sin(theta*4+index*.35+phase) +
                   0.002 * np.sin(theta*9-index*.2+phase*.35))
        rows.append(np.column_stack((center_x+(rx+flutter)*cx, cy+(ry+flutter)*sy, np.full(n,z))))
    _grid(builder, material, rows)


def _path_interp(points, steps=5):
    p=np.asarray(points, dtype=float)
    if len(p)<2: raise ValueError('Path too short')
    result=[]
    for k in range(len(p)-1):
        a=p[max(0,k-1)]; b=p[k]; c=p[k+1]; d=p[min(k+2,len(p)-1)]
        for u in np.linspace(0,1,steps,endpoint=False):
            # Catmull-Rom: smooth but bounded authored path, no abrupt strap kinks.
            result.append(.5*((2*b)+(-a+c)*u+(2*a-5*b+4*c-d)*u*u+(-a+3*b-3*c+d)*u*u*u))
    result.append(p[-1]); return np.asarray(result)


def ribbon(builder,material,points,widths,thickness=.009,steps=5):
    """Variable-width 3D fabric ribbon rather than a round, floating tube."""
    point_arr=np.asarray(points,dtype=float)
    widths=np.asarray(widths,dtype=float)
    if (point_arr.ndim!=2 or point_arr.shape[1]!=3 or not 2<=len(point_arr)<=64 or
        len(widths)!=len(point_arr) or np.any(widths<=0) or
        np.max(widths)>5 or not np.isfinite(point_arr).all() or
        not np.isfinite(widths).all() or not 0<thickness<=.5 or
        np.max(np.abs(point_arr))>50):
        raise ValueError('Invalid bounded ribbon geometry')
    p=_path_interp(point_arr,steps)
    xs=np.linspace(0,len(p)-1,len(widths))
    w=np.interp(np.arange(len(p)),xs,widths)
    rings=[]
    for k,q in enumerate(p):
        tangent=p[min(k+1,len(p)-1)]-p[max(0,k-1)]
        tangent/=max(np.linalg.norm(tangent),1e-8)
        # Width direction prefers horizontal X, continuously projected onto tangent plane.
        side=np.array([1.,0.,0.]); side-=tangent*np.dot(tangent,side)
        side/=max(np.linalg.norm(side),1e-8)
        normal=np.cross(tangent,side);normal/=max(np.linalg.norm(normal),1e-8)
        rings.append([q-side*w[k]*.5-normal*thickness*.5,
                      q+side*w[k]*.5-normal*thickness*.5,
                      q+side*w[k]*.5+normal*thickness*.5,
                      q-side*w[k]*.5+normal*thickness*.5])
    _grid(builder,material,rings)


def _ring_loop(builder, points, radius,material):
    pts=np.asarray(points,dtype=float)
    if len(pts) <= 64:builder.tube(pts,radius,material,sides=7)
    else:
        for i in range(0,len(pts)-1,60):
            builder.tube(pts[i:min(i+61,len(pts))],radius,material,sides=7)


def avocado(builder, seed=0, variant=0):
    """Longitudinally halved pear-shaped avocado: convex back, cut face, pit cavity.

    Intentional open cut is not an accidental missing polygon. The rind is a real
    thickness; the flesh face spans the pear outline to a depressed seed pocket.
    """
    scale=1+.008*((variant%5)-2)
    n=72; t=np.linspace(0,TAU,n,endpoint=False)
    # Pear outline: large lower shoulder, tighter top; slightly asymmetrical.
    zc=.225; zr=.22
    zz=zc+zr*np.sin(t)
    rx=(.158-.033*np.sin(t))*(1+.03*np.sin(2*t+seed*.01))
    xx=rx*np.cos(t)
    outline=np.column_stack((xx,np.zeros(n),zz))*scale
    # Volumetric convex rear, all in Y >= 0. Cut is explicitly oriented toward -Y.
    skin_rows=[]
    for fraction in np.linspace(0,1,23):
        f=1-.975*fraction**1.45
        y=.24*np.sin(fraction*np.pi/2)
        radial=outline.copy()
        radial[:,0]*=f
        radial[:,2]=zc*scale+(radial[:,2]-zc*scale)*f
        radial[:,1]=y+(.0011*np.sin(t*17+fraction*8+seed))
        skin_rows.append(radial)
    _surface(builder,'skin',skin_rows)
    # Cap the tiny rear pole: no giant triangle fan across the visible face.
    back_center=np.array([0,.24,zc*scale]);last=skin_rows[-1]
    verts=np.vstack((last,back_center)); faces=[]
    for j in range(n): faces.append((n,(j+1)%n,j))
    builder.add('skin',verts,faces)
    # Actual exposed rind, pale green under-skin band, and yellow-green interior.
    def offset_ring(f,y):
        r=outline.copy();r[:,0]*=f;r[:,2]=zc*scale+(r[:,2]-zc*scale)*f;r[:,1]=y
        return r
    _surface(builder,'skin_dark',[offset_ring(1,-.004),offset_ring(.965,-.015)])
    _surface(builder,'flesh_green',[offset_ring(.965,-.016),offset_ring(.90,-.024)])
    # Soft, subtly concave flesh, not a floating oval placed over the skin.
    inner_flesh=offset_ring(.90,-.025)
    pit_z=.165*scale
    hole=np.column_stack((.057*np.cos(t),np.full(n,.003),pit_z+.068*np.sin(t)))
    flesh_rows=[]
    for f in np.linspace(0,1,8):
        r=inner_flesh*(1-f)+hole*f
        r[:,1]=(-.025+ .026*f + .002*np.cos(t*5)*(1-f)*f)
        flesh_rows.append(r)
    _surface(builder,'flesh',flesh_rows)
    # Inset pit ring is a darker flesh boundary, not a material painted over solid flesh.
    hole_ring=np.column_stack((.065*np.cos(t),np.full(n,-.001),pit_z+.076*np.sin(t)))
    _surface(builder,'pit_shadow',[hole_ring,hole])
    # Seed in the visible cavity, protruding just past the front cut plane.
    builder.ellipsoid([0,-.031,pit_z],[.050,.046,.058],'pit',32,17,1.05)
    builder.ellipsoid([-.016,-.074,pit_z+.012],[.014,.003,.020],'pit_light',16,8)
    # Small stem remnant at the narrow end.
    builder.tube([[0,.05,.443*scale],[.008,.055,.467*scale]],.008,'wood',sides=9)
    # The dark rind border provides readable depth at icon and inspection scale.
    return {'recognition_markers':['pear silhouette','open cut face','rind thickness','recessed brown pit']}


def backpack(builder, seed=0, variant=0):
    """Softgoods: asymmetric padded loft, sewn pouch volumes and 3D shoulder harness."""
    h=.73*(1+.008*((variant%5)-2))
    superloft(builder,'fabric',[
        (.025,.19,.083,.01),(.07,.265,.115,.005),(.19,.299,.144,0),
        (.40,.309,.158,.007),(.58,.299,.142,.017),(.70,.224,.111,.026),
        (.765,.09,.065,.035),(.775,.01,.015,.035)], n=44,exponent=2.85,noise_seed=seed)
    # Front outer panel is real surface volume. The pouch projects past the torso.
    superloft(builder,'fabric_light',[
        (.105,.14,.055,-.167),(.12,.198,.072,-.185),(.17,.226,.080,-.201),
        (.29,.235,.081,-.202),(.39,.216,.073,-.196),(.42,.15,.05,-.181),(.43,.02,.023,-.17)],
        n=40,exponent=3.1,noise_seed=seed+17)
    # Flat-ish broad lower fabric panel with a raised flap / rolled top seam.
    _ring_loop(builder,[[-.210,-.230,.393],[-.140,-.251,.414],[-.01,-.254,.427],
                        [.14,-.251,.414],[.210,-.230,.393]],.010,'fabric_dark')
    # Pocket two zipper rails and metal zipper pull centered on front.
    for z in (.355,.370):
        _ring_loop(builder,[[-.170,-.264,z],[-.095,-.279,z+.004],[0,-.284,z+.008],
                            [.095,-.279,z+.004],[.170,-.264,z]],.005,'fabric_dark')
    builder.box([.105,-.292,.375],[.021,.018,.022],'steel')
    _ring_loop(builder,[[.105,-.299,.366],[.109,-.306,.343]],.006,'steel')
    # Seams follow the pocket curve (no random hovering rectangles).
    for x in (-.19,.19):
        _ring_loop(builder,[[x,-.222,.18],[x*1.03,-.267,.21],[x*1.04,-.273,.31],
                            [x,-.244,.39]],.004,'seam')
    _ring_loop(builder,[[-.21,-.212,.15],[-.10,-.255,.132],[0,-.260,.13],
                        [.10,-.255,.132],[.21,-.212,.15]],.004,'seam')
    # Two padded back straps. They are extruded fabric ribbons, not round tubing.
    for side in (-1,1):
        s=float(side)
        p=[[s*.155,.10,.675],[s*.185,.205,.66],[s*.235,.276,.52],
           [s*.248,.282,.345],[s*.214,.204,.14],[s*.195,.137,.07]]
        ribbon(builder,'fabric_dark',p,[.065,.072,.084,.083,.065,.055],.019)
        # Side pouches made of soft volumes with real attachment onto side body.
        superloft(builder,'fabric_light',[(.12,.054,.051,-.015),(.17,.067,.073,-.018),
            (.25,.067,.075,-.018),(.325,.050,.060,-.013),(.34,.015,.025,-.010)],
            n=22,exponent=2.5,noise_seed=seed+19+side,center_x=s*.286)
        # A strap running around each side pocket / compression buckle.
        x=s*.278
        ribbon(builder,'fabric_dark',[[x,-.075,.335],[x,-.12,.322],[x,-.15,.286],
                                       [x,-.135,.240],[x,-.08,.234]],[.027]*5,.007)
        builder.box([s*.283,-.155,.285],[.037,.022,.046],'black')
        builder.box([s*.283,-.171,.286],[.016,.008,.025],'steel')
    # Top carry handle, thicker root patches and neckline zipper.
    ribbon(builder,'fabric_dark',[[-.085,.02,.738],[-.07,.015,.817],[0,.012,.837],
                                   [.07,.015,.817],[.085,.02,.738]],[.043,.044,.047,.044,.043],.019)
    for side in (-1,1):
        builder.box([side*.084,.010,.730],[.071,.039,.037],'fabric_dark')
    _ring_loop(builder,[[-.17,-.09,.700],[0,-.12,.725],[.17,-.09,.700]],.007,'black')
    # Top broad stiffening panel and deliberately placed stitch dots.
    builder.box([0,-.119,.673],[.26,.019,.031],'fabric_dark')
    stitchv=[]; stitchf=[]
    for x in np.linspace(-.15,.15,19):
        # Tiny surface stitched diamonds in one draw component.
        j=len(stitchv);yy=-.268
        stitchv.extend([[x-.002,yy,.149],[x+.002,yy,.149],[x,yy-.002,.153]])
        stitchf.append((j,j+1,j+2))
    builder.add('stitch',stitchv,stitchf)
    return {'recognition_markers':['padded tapered body','raised front pocket','zipper','fabric shoulder straps','top handle']}


def _head_bevel(builder, xs, top, bottom, thickness, material='steel'):
    """True double-sided tapered axe blade: thickness collapses at sharp edge."""
    xs=np.asarray(xs,float); top=np.asarray(top,float); bottom=np.asarray(bottom,float)
    thickness=np.asarray(thickness,float)
    n=len(xs)
    if (len(top)!=n or len(bottom)!=n or len(thickness)!=n or not 3<=n<=60 or
        not (np.isfinite(xs).all() and np.isfinite(top).all() and
             np.isfinite(bottom).all() and np.isfinite(thickness).all()) or
        np.any(top<=bottom) or np.any(thickness<=0) or np.any(np.diff(xs)<=0) or
        max(np.max(np.abs(xs)),np.max(np.abs(top)),np.max(np.abs(bottom)))>50):
        raise ValueError('Invalid cutting head sections')
    v=[]
    for x,zt,zb,d in zip(xs,top,bottom,thickness):
        v.extend([[x,-d/2,zt],[x,-d/2,zb],[x,d/2,zt],[x,d/2,zb]])
    f=[]
    for i in range(n-1):
        a=4*i;b=4*(i+1)
        # negative Y cheek and positive Y cheek, upper and lower transitions
        f.extend([(a,b,b+1),(a,b+1,a+1), (a+2,b+3,b+2),(a+2,a+3,b+3),
                  (a,b+2,b),(a+2,b+2,a+0), (a+1,b+1,b+3),(a+1,b+3,a+3)])
    f.extend([(0,1,3),(0,3,2)])
    q=4*(n-1);f.extend([(q,q+2,q+3),(q,q+3,q+1)])
    builder.add(material,v,f)


def _handle(builder,profile,n=20):
    rows=[]
    theta=np.linspace(0,TAU,n,endpoint=False)
    for z,x,rx,ry in profile:
        rows.append(np.column_stack((x+rx*np.cos(theta),ry*np.sin(theta),np.full(n,z))))
    _grid(builder,'wood',rows)


def axe(builder, seed=0, variant=0):
    """Slim curved hardwood haft; forged flared head with physically tapered cheeks."""
    zscale=1+((variant%5)-2)*.009
    # An authored, smoothly curved handle section rather than a basic lathed cone.
    profile=[(0,.025,.043,.036),(.045,.024,.041,.032),(.125,.021,.031,.028),
        (.27,.019,.028,.026),(.42,.004,.026,.025),(.60,-.006,.025,.023),
        (.78,-.009,.028,.024),(.87,-.009,.035,.028),(.97,-.009,.034,.029),
        (1.02,-.008,.030,.026)]
    profile=[(z*zscale,x,rx,ry) for z,x,rx,ry in profile]
    _handle(builder,profile)
    # Subtle vertical grain, physically attached to the wooden shaft.
    for yy in (-.014,.014):
        _ring_loop(builder,[[.01,yy,.14],[.005,yy,.33],[-.009,yy,.51],
                            [-.016,yy,.72]],.0025,'wood_grain')
    # Ergonomic lower-end oval grip with a small wooden end cap.
    _grid(builder,'wood_dark',[np.column_stack((.025+.045*np.cos(np.linspace(0,TAU,20,endpoint=False)),
                    .032*np.sin(np.linspace(0,TAU,20,endpoint=False)),np.full(20,.006))),
                    np.column_stack((.024+.039*np.cos(np.linspace(0,TAU,20,endpoint=False)),
                    .029*np.sin(np.linspace(0,TAU,20,endpoint=False)),np.full(20,.041)))])
    # Forge construction: cheek is widest at eye, narrows to ~2mm at cutting edge.
    zh=.885*zscale
    xs=[-.470,-.430,-.388,-.345,-.300,-.255,-.200,-.146,-.075,-.012,.076,.140]
    upper=[.194,.195,.174,.140,.118,.106,.096,.084,.081,.079,.073,.056]
    lower=[-.192,-.192,-.176,-.137,-.110,-.095,-.079,-.070,-.069,-.069,-.065,-.054]
    thick=[.002,.004,.012,.027,.039,.052,.060,.067,.076,.082,.071,.052]
    _head_bevel(builder,xs,[zh+a for a in upper],[zh+a for a in lower],thick,'steel')
    # Polished cutting-edge bevel is genuinely tapered in volume.
    _head_bevel(builder,[-.471,-.449,-.432,-.405,-.378],
                [zh+a for a in (.196,.195,.190,.181,.169)],
                [zh+a for a in (-.194,-.195,-.187,-.181,-.166)],
                [.0015,.002,.0045,.008,.015],'edge')
    # Forged eye/socket, following the handle without an enormous box-block head.
    builder.rings([(zh-.075,.048),(zh-.045,.053),(zh+.06,.052),(zh+.079,.047)],
                  [-.008,0,0],'steel_dark',n=18,rx=1,ry=.82)
    builder.rings([(zh+.078,.051),(zh+.089,.049)],[-.008,0,0],'steel',n=18,rx=1,ry=.82)
    # Edge line that remains visible from front and opposite quarter view.
    builder.tube([[-.468,-.001,zh-.185],[-.495,-.001,zh-.07],
                  [-.501,-.001,zh+.08],[-.469,-.001,zh+.19]],.0025,'edge',sides=6)
    return {'recognition_markers':['slender shaped haft','tapered double-bevel steel head',
                                    'flared cutting edge','forged eye socket']}


BUILDERS = {'avocado':avocado,'backpack':backpack,'axe':axe}


def beam(builder,material,start,end,width,depth):
    """Oriented structural prismatic member, rather than a diagonal-looking box."""
    a=np.asarray(start,float);b=np.asarray(end,float)
    t=b-a;l=np.linalg.norm(t)
    if l<=1e-5 or width<=0 or depth<=0 or not np.isfinite(l):
        raise ValueError('Invalid structural beam')
    t=t/l
    ref=np.array([0.,1.,0.])
    if abs(np.dot(t,ref))>.92:ref=np.array([0.,0.,1.])
    u=np.cross(t,ref);u/=np.linalg.norm(u)
    v=np.cross(t,u)
    # Real eight-corner chamfer cross section, retaining four major flat faces.
    hw=width*.5;hd=depth*.5;bev=min(width,depth)*.10
    profile=[(-hw+bev,-hd),(hw-bev,-hd),(hw,-hd+bev),(hw,hd-bev),
             (hw-bev,hd),(-hw+bev,hd),(-hw,hd-bev),(-hw,-hd+bev)]
    corners=[u*i+v*j for i,j in profile]
    verts=[a+c for c in corners]+[b+c for c in corners]
    faces=[];n=len(profile)
    for j in range(1,n-1):
        faces.extend(((0,j+1,j),(n,n+j,n+j+1)))
    for k in range(n):
        j=(k+1)%n
        faces.extend(((k,j,j+n),(k,j+n,k+n)))
    builder.add(material,verts,faces)


def wearable_shell(builder,material,sections,n=48,depth_ratio=.76):
    """Real hollow torso thickness with uncovered neck/bottom openings.

    Creates geometry around the interior, not a closed solid mannequin under
    the armor. The inside geometry and annular top/bottom edges remain editable.
    """
    profiles=_smooth_sections(sections,3)
    theta=np.linspace(0,TAU,n,endpoint=False)
    outer=[];inner=[]
    for z,rx,ry,cy in profiles:
        cx=np.cos(theta);sn=np.sin(theta)
        # Ellipse is a control shape; panels later give vest its front anatomy.
        outer.append(np.column_stack((rx*cx,cy+ry*sn,np.full(n,z))))
        inner.append(np.column_stack(((rx-.016)*cx,cy+(ry-.015)*sn,np.full(n,z))))
    _grid(builder,material,outer,caps=False)
    # Reverse face winding to orient normals toward hollow interior.
    r=np.asarray(inner)[::-1,::-1,:]
    _grid(builder,material,r,caps=False)
    _surface(builder,material,[outer[0],inner[0][::-1][::-1]])
    _surface(builder,material,[outer[-1],inner[-1]])


def armor(builder,seed=0,variant=0):
    """Segmented padded protective vest with shaped torso shell and real panel hierarchy."""
    sw=1+.012*((variant%5)-2)
    wearable_shell(builder,'fabric_dark',[
        (.13,.22*sw,.09,0),(.18,.28*sw,.13,0),(.34,.285*sw,.142,0),
        (.54,.34*sw,.161,0),(.70,.39*sw,.147,.007),(.80,.292*sw,.126,.02),
        (.85,.18*sw,.090,.025)],n=48)
    # Separate anatomically shaped cuirass panels, not a rigid rectangular box.
    for side in (-1,1):
        s=float(side)
        builder.ellipsoid([s*.168,-.157,.586],[.157,.051,.205],
                          'olive',segments=32,rings=15,boxiness=.72)
        builder.ellipsoid([s*.153,-.158,.315],[.155,.040,.119],
                          'fabric_light',segments=26,rings=12,boxiness=.70)
        builder.ellipsoid([s*.355,.017,.76],[.146,.139,.080],
                          'steel_dark',segments=22,rings=11,boxiness=.88)
        # Shoulder harness uses broad flexible shaped ribbon segments.
        ribbon(builder,'leather',[[s*.177,-.18,.78],[s*.207,-.05,.86],
                                 [s*.219,.10,.846],[s*.19,.153,.72]],
                [.071,.079,.084,.078],thickness=.022)
        for j in range(3):
            z=.48+j*.076
            builder.box([s*.163,-.205,z],[.22,.014,.018],'fabric_dark')
        for j in range(2):
            builder.box([s*.15,-.205,.25+j*.068],[.208,.012,.018],'seam')
        # Side adjustable belt with buckle and soft fabric retention loops.
        ribbon(builder,'fabric',[[s*.265,-.08,.34],[s*.31,.008,.34],[s*.285,.115,.34]],
               [.053,.050,.048],thickness=.016)
        builder.box([s*.295,-.13,.345],[.038,.031,.038],'steel')
        builder.box([s*.295,-.146,.345],[.016,.012,.016],'black')
    # Left/right hardplate join seam, framed central quick-release tab.
    builder.box([0,-.215,.58],[.012,.015,.335],'fabric_dark')
    builder.box([0,-.218,.42],[.042,.025,.062],'steel_dark')
    # Three external accessory pouches, empty, attached to lower vest face.
    for x in (-.185,0,.185):
        builder.ellipsoid([x,-.191,.207],[.080,.042,.060],
                          'fabric',segments=18,rings=10,boxiness=.57)
        builder.box([x,-.233,.228],[.122,.008,.013],'fabric_dark')
        builder.box([x,-.238,.216],[.027,.011,.028],'steel')
    # Exterior padded collar below neck, center remains open in silhouette.
    ribbon(builder,'fabric_light',[[-.18,-.045,.846],[-.075,-.104,.848],[0,-.109,.850],
                                   [.075,-.104,.848],[.18,-.045,.846]],
           [.058,.066,.059,.066,.058],thickness=.025)
    return {'recognition_markers':['tapered chest silhouette','segmented armor panels',
                                    'shoulder straps','MOLLE webbing','side buckles','attached pouches']}


def shelf(builder,seed=0,variant=0):
    """Empty metal shelving with actual crossed rear braces and folded lips."""
    w=1.12+.025*(variant%4);d=.46;h=1.62+.012*(variant%6)
    # Four upright vertical cold-formed channels with stiffening edges.
    for x in (-w/2,w/2):
        for y in (-d/2,d/2):
            builder.box([x,y,h/2],[.048,.034,h],'steel_dark')
            builder.box([x,y-.017,h/2],[.018,.015,h],'steel')
            builder.box([x,y,.019],[.071,.075,.038],'black')
    levels=[.18,.60,1.03,1.46]
    for i,z in enumerate(levels):
        # Shelf deck, front/back return bends, and side lips.
        builder.box([0,0,z],[w+.038,d+.02,.027],'steel')
        for y in (-d/2,d/2):
            builder.box([0,y,z+.027],[w+.036,.023,.057],'steel_dark')
        for x in (-w/2,w/2):
            builder.box([x,0,z+.018],[.020,d,.047],'paint_light')
        for x in (-w*.43,w*.43):
            # Under-deck ribs, do not accidentally put objects ON the shelf.
            beam(builder,'steel_dark',[x,-d*.39,z-.055],
                 [x,+d*.39,z-.055],.023,.029)
    # Back X bracing, connected between the upright structural junctions.
    y=d/2+.022
    beam(builder,'steel_dark',[-w/2,y,.15],[w/2,y,h-.13],.029,.017)
    beam(builder,'steel_dark',[w/2,y,.15],[-w/2,y,h-.13],.029,.017)
    builder.box([0,y+.014,h*.50],[.075,.020,.075],'steel')
    # Small bolt-heads are geometry and placed at frame connections.
    for z in (.16,h-.13):
        for x in (-w/2,w/2):
            builder.box([x,y+.017,z],[.026,.010,.027],'edge')
    return {'recognition_markers':['four steel uprights','four empty shelves',
                                    'folded tray lips','real diagonal rear braces','foot pads']}

BUILDERS.update({'armor':armor,'shelf':shelf})


def bottle(builder,seed=0,variant=0):
    """Empty blown-glass vessel with physically modeled neck, rolled lip and label."""
    # A smooth molded glass bottle profile, not a set of stacked cylinders.
    scale=1+.02*(variant%3)
    builder.rings([(0,.042),(.012,.068),(.036,.087),(.09,.092),(.22,.088),
                   (.32,.080),(.355,.065),(.385,.043),(.425,.033),(.458,.033)],
                  [0,0,0],'glass',n=32,rx=scale,ry=scale)
    builder.rings([(.455,.034),(.461,.039),(.475,.039),(.483,.033)],
                  [0,0,0],'glass',n=32)
    # Opaque cap in a separate attached part. Bottle stays empty, no liquid proxy.
    builder.rings([(.480,.034),(.507,.034),(.512,.030)],[0,0,0],
                  'steel_dark',n=30)
    # Label wraps the actual circumference of the vessel, with top/bottom paper edges.
    builder.rings([(.145,.089),(.155,.091),(.231,.090),(.242,.089)],
                  [0,0,0],'white',n=32)
    builder.rings([(.173,.091),(.177,.092),(.184,.092),(.189,.091)],
                  [0,0,0],'red',n=32)
    return {'recognition_markers':['molded glass body','narrow neck','rolled lip','label','cap']}


def barrel(builder,seed=0,variant=0):
    """Ribbed rolled-sheet steel barrel with two embossed closed ends."""
    r=.25+.004*(variant%4)
    builder.rings([(0,r*.86),(.018,r*.93),(.070,r),(.21,r*1.027),(.39,r*1.035),
                   (.57,r*1.025),(.73,r),(.79,r*.92),(.81,r*.87)],
                  [0,0,0],'paint',n=36)
    for z in (.036,.252,.535,.766):
        builder.rings([(z-.018,r*1.005),(z-.01,r*1.058),
                       (z+.012,r*1.058),(z+.02,r*1.005)],
                      [0,0,0],'steel_dark',n=36)
    # Lid/dome top is closed; no fictional contents.
    builder.rings([(.804,.217),(.816,.200),(.818,.105),(.818,.01)],
                  [0,0,0],'steel',n=36)
    for x in (-.105,.115):
        builder.rings([(.818,.019),(.824,.023),(.832,.022)],
                      [x,0,0],'steel_dark',n=18)
    # Vertical weld seam / real thin raised bead.
    _ring_loop(builder,[[r*1.013,-.003,.06],[r*1.040,-.003,.27],
                        [r*1.043,-.003,.54],[r*1.013,-.003,.73]],
               .003,'steel_dark')
    return {'recognition_markers':['steel rolled barrel','swaged reinforcement ribs',
                                    'embossed closed lid','weld seam']}


def crate(builder,seed=0,variant=0):
    """Open-top wooden slat crate. Empty and internally unobstructed by design."""
    w=.66+.015*(variant%4);d=.46;h=.44
    builder.box([0,0,.029],[w-.040,d-.038,.038],'wood_dark')
    # Structural corner posts, with internal void and slatted opposing sides.
    for sx in (-1,1):
        for sy in (-1,1):
            builder.box([sx*(w/2-.027),sy*(d/2-.027),h/2],
                        [.046,.046,h],'wood_dark')
    for z in (.095,.20,.305,.40):
        for sy in (-1,1):
            builder.box([0,sy*(d/2-.021),z],[w-.04,.028,.077],'wood')
        for sx in (-1,1):
            builder.box([sx*(w/2-.021),0,z],[.028,d-.04,.077],'wood')
    # Front slat wood grain and black recessed hand holes are visibly attached.
    builder.box([0,-d/2-.039,.290],[.180,.010,.028],'wood_dark')
    for yy in (-d/2-.036,d/2+.036):
        for x in (-w*.31,w*.31):
            builder.box([x,yy,.406],[.016,.007,.014],'steel_dark')
    return {'recognition_markers':['open empty interior','four posts','real slat gaps',
                                    'base board','corner joins']}


def helmet(builder,seed=0,variant=0):
    """Hollow protective helmet with fitted lip, raised central rib and chinstrap."""
    # Thin outer curvature. Bottom remains intentionally open.
    theta=np.linspace(0,TAU,36,endpoint=False)
    rows=[]
    for z,rx,ry in [(.112,.214,.230),(.145,.239,.246),(.223,.246,.262),
                    (.311,.222,.240),(.368,.168,.190),(.417,.101,.125),(.448,.025,.030)]:
        rows.append(np.column_stack((rx*np.cos(theta),ry*np.sin(theta),np.full(36,z))))
    _grid(builder,'steel',rows,caps=False)
    inner=[]
    for z,rx,ry in [(.107,.204,.222),(.143,.227,.235),(.220,.234,.250),
                     (.309,.211,.229),(.365,.159,.180),(.415,.095,.117),(.442,.020,.023)]:
        inner.append(np.column_stack((rx*np.cos(theta),ry*np.sin(theta),np.full(36,z))))
    _grid(builder,'steel_dark',inner,caps=False)
    _surface(builder,'steel_dark',[rows[0],inner[0]])
    _surface(builder,'steel_dark',[rows[-1],inner[-1]])
    # Shaped bill and brow panel, not a rectangular intersecting box.
    outline=[(-.22,.117),(-.17,.095),(-.08,.080),(0,.077),(.08,.080),(.17,.095),(.22,.117),
             (.20,.146),(-.20,.146)]
    # Brim extends front -Y; loft two thin curved strips.
    _grid(builder,'steel_dark',[np.array([[x,-.26+.1*abs(x),z] for x,z in outline]),
                                np.array([[x,-.306+.1*abs(x),z-.008] for x,z in outline])])
    _ring_loop(builder,[[-.226,-.081,.128],[-.185,-.190,.118],[-.070,-.287,.103],
                        [.07,-.287,.103],[.185,-.190,.118],[.226,-.081,.128]],.009,'black')
    # Reinforced crown ridge and panel fastening rivets.
    _ring_loop(builder,[[0,-.226,.17],[0,-.226,.26],[0,-.194,.35],
                        [0,-.096,.421],[0,.027,.449]],.009,'steel_dark')
    for sx in (-1,1):
        builder.ellipsoid([sx*.20,-.10,.15],[.019,.015,.015],'edge',12,6)
        ribbon(builder,'leather',[[sx*.202,-.018,.135],[sx*.190,.10,.045],
                                 [sx*.110,.17,.015]], [.032,.037,.028],thickness=.007)
    return {'recognition_markers':['hollow head shell','curved brim','crown reinforcement','chinstrap']}


def medkit(builder,seed=0,variant=0):
    """Soft zippered medical bag with raised front applique and sewn top carry handle."""
    superloft(builder,'red',[(.025,.21,.12,0),(.048,.30,.16,0),
        (.16,.34,.17,0),(.315,.33,.165,0),(.44,.255,.14,.012),(.48,.10,.08,.017)],
        n=36,exponent=2.6,noise_seed=seed)
    # Padded red front patch with a raised white fabric cross (not a texture emoji).
    builder.ellipsoid([0,-.178,.250],[.176,.025,.132],
                      'red',segments=30,rings=12,boxiness=.68)
    builder.box([0,-.210,.255],[.173,.017,.048],'white')
    builder.box([0,-.212,.255],[.051,.019,.182],'white')
    # Real closure route across curved upper flap.
    _ring_loop(builder,[[-.24,-.10,.405],[-.17,-.136,.437],[0,-.160,.451],
                        [.17,-.136,.437],[.24,-.10,.405]],.011,'steel_dark')
    builder.box([.145,-.151,.440],[.017,.021,.028],'steel')
    ribbon(builder,'fabric_dark',[[-.11,.03,.45],[-.11,.03,.55],
                                   [0,.03,.565],[.11,.03,.55],[.11,.03,.45]],
           [.040,.044,.047,.044,.040],.015)
    for sx in (-1,1):builder.box([sx*.11,.03,.45],[.067,.042,.034],'red')
    return {'recognition_markers':['rounded medical bag','raised medical cross',
                                    'zipper track','fabric carry handle']}


def chair(builder,seed=0,variant=0):
    """Wooden chair with true slanted rear supports and curved seat cushion."""
    w=.53;d=.51
    for sx in (-1,1):
        for sy in (-1,1):
            bottom=[sx*.215,sy*.22,.019]
            top=[sx*.215,sy*.20,.45]
            beam(builder,'wood_dark',bottom,top,.041,.039)
    # Contoured wooden seat + thin upholstery; keep separable material regions.
    superloft(builder,'wood',[(.414,.235,.23,0),(.426,.260,.256,0),
                              (.465,.245,.242,0),(.478,.20,.205,0)],
              n=30,exponent=3.1,noise_seed=seed)
    superloft(builder,'leather',[(.477,.207,.216,0),(.481,.232,.231,0),
                                 (.50,.200,.205,0)],n=30,exponent=2.9,noise_seed=seed+2)
    # Angled rear posts go all the way from the floor to backrest crown.
    for sx in (-1,1):
        beam(builder,'wood_dark',[sx*.224,.22,.018],[sx*.234,.253,1.01],.048,.044)
    # Four carved backrest horizontal boards, slightly curved rather than one box.
    for z in (.62,.72,.83,.94):
        ribbon(builder,'wood',[[-.23,.246,z-.013],[-.09,.222,z],
                              [.09,.222,z],[.23,.246,z-.013]],
               [.065,.078,.078,.065],thickness=.029)
    # Support braces under seat to visually ground the four legs.
    for sx in (-1,1):
        beam(builder,'wood',[sx*.218,-.19,.32],[sx*.218,.21,.32],.024,.022)
    return {'recognition_markers':['four true legs','carved curved seat','slanted rear supports',
                                    'separate backrest slats']}


def canister(builder,seed=0,variant=0):
    """Molded jerrycan with recessed vertical channels and screw-cap nozzle."""
    superloft(builder,'olive',[(.035,.150,.093,0),(.065,.190,.109,0),
        (.22,.203,.112,0),(.44,.201,.111,0),(.545,.168,.099,0),
        (.594,.120,.070,0)],n=32,exponent=3.25,noise_seed=seed)
    # Three embossed vertical flutes in the front face.
    for xx in (-.112,0,.112):
        ribbon(builder,'paint',[[xx,-.111,.160],[xx,-.123,.25],
                                [xx,-.121,.40],[xx,-.105,.48]],
               [.017,.024,.024,.017],thickness=.008)
    builder.box([0,-.111,.115],[.26,.021,.035],'steel_dark')
    # Handle loop is real geometry, with clearance between grip and body.
    ribbon(builder,'steel_dark',[[-.098,0,.568],[-.10,0,.653],[-.075,0,.675],
                                  [.075,0,.675],[.10,0,.653],[.098,0,.568]],
           [.042,.049,.052,.052,.049,.042],thickness=.033)
    # Raised cylindrical fill neck, removable cap geometry; no contents.
    builder.rings([(.557,.034),(.630,.035),(.635,.046),(.674,.046)],
                  [.126,0,0],'steel_dark',n=24)
    builder.rings([(.676,.051),(.685,.051)],[.126,0,0],'edge',n=24)
    for z in (.648,.657,.667):
        builder.rings([(z,.047),(z+.002,.048)],[.126,0,0],'black',n=24)
    return {'recognition_markers':['molded jerrycan body','reinforcing flutes',
                                    'openable carry-handle space','separate screw cap']}

BUILDERS.update({'bottle':bottle,'barrel':barrel,'crate':crate,'helmet':helmet,
                 'medkit':medkit,'chair':chair,'canister':canister})
