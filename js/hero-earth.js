/**
 * Interactive 3D Earth for EARS-CONN hero (same logic as /testpage; textures from /images/earth-3d/).
 */
import * as THREE from 'https://esm.sh/three@0.161.0';

(function () {
  const mount = document.getElementById('heroEarthScene');
  if (!mount) return;

  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const scene = new THREE.Scene();
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(mount.clientWidth, mount.clientHeight);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  mount.appendChild(renderer.domElement);

  const camera = new THREE.PerspectiveCamera(36, mount.clientWidth / mount.clientHeight, 0.1, 100);
  camera.position.set(0, 0, 6.7);

  const ambient = new THREE.AmbientLight(0x8fdcff, 1.6);
  scene.add(ambient);

  const sun = new THREE.DirectionalLight(0xffffff, 2.6);
  sun.position.set(4, 2, 5);
  scene.add(sun);

  const rim = new THREE.DirectionalLight(0x60a5fa, 1.6);
  rim.position.set(-5, -1.5, -4);
  scene.add(rim);

  const textureLoader = new THREE.TextureLoader();

  function loadTexture(path) {
    const texture = textureLoader.load(path);
    texture.colorSpace = THREE.SRGBColorSpace;
    return texture;
  }

  const earthGroup = new THREE.Group();
  scene.add(earthGroup);

  const earthTexture = loadTexture('images/earth-3d/albedo.jpg?v=2');
  const bumpTexture = textureLoader.load('images/earth-3d/bump.jpg?v=2');
  const nightTexture = loadTexture('images/earth-3d/night-lights.png?v=2');
  const landOceanMask = textureLoader.load('images/earth-3d/land-ocean-mask.png?v=2');

  bumpTexture.colorSpace = THREE.NoColorSpace;
  landOceanMask.colorSpace = THREE.NoColorSpace;
  const earth = new THREE.Mesh(
    new THREE.SphereGeometry(2, 96, 96),
    new THREE.MeshPhongMaterial({
      map: earthTexture,
      bumpMap: bumpTexture,
      bumpScale: 0.1,
      specularMap: landOceanMask,
      emissiveMap: nightTexture,
      emissive: new THREE.Color('#ffb347'),
      emissiveIntensity: 0.4,
      shininess: 16,
      specular: new THREE.Color('#a7d8ff'),
    })
  );
  earthGroup.add(earth);

  const cloudTexture = textureLoader.load('images/earth-3d/clouds.png?v=2');
  cloudTexture.colorSpace = THREE.SRGBColorSpace;

  const clouds = new THREE.Mesh(
    new THREE.SphereGeometry(2.04, 64, 64),
    new THREE.MeshPhongMaterial({
      map: cloudTexture,
      transparent: true,
      opacity: 0.34,
      depthWrite: false,
    })
  );
  earthGroup.add(clouds);

  const atmosphere = new THREE.Mesh(
    new THREE.SphereGeometry(2.18, 64, 64),
    new THREE.MeshBasicMaterial({
      color: 0x4cc9ff,
      transparent: true,
      opacity: 0.14,
      side: THREE.BackSide,
    })
  );
  earthGroup.add(atmosphere);

  const starsGeometry = new THREE.BufferGeometry();
  const starCount = 1200;
  const starVertices = new Float32Array(starCount * 3);
  for (let i = 0; i < starCount; i++) {
    const radius = 16 + Math.random() * 20;
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(2 * Math.random() - 1);
    starVertices[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
    starVertices[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
    starVertices[i * 3 + 2] = radius * Math.cos(phi);
  }
  starsGeometry.setAttribute('position', new THREE.BufferAttribute(starVertices, 3));

  const stars = new THREE.Points(
    starsGeometry,
    new THREE.PointsMaterial({
      color: 0xdbeafe,
      size: 0.06,
      transparent: true,
      opacity: 0.85,
    })
  );
  scene.add(stars);

  const pointer = { x: 0, y: 0 };
  const zoom = {
    min: 4.3,
    max: 9.2,
    current: 6.7,
    target: 6.7,
  };
  const drag = {
    active: false,
    lastX: 0,
    lastY: 0,
    rotationX: 0,
    rotationY: 0,
  };
  const activePointers = new Map();
  let pinchDistance = null;
  let rafId = null;

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function distanceBetweenPointers(a, b) {
    const dx = a.x - b.x;
    const dy = a.y - b.y;
    return Math.hypot(dx, dy);
  }

  function updateZoom(delta) {
    zoom.target = clamp(zoom.target + delta, zoom.min, zoom.max);
  }

  function onPointerMove(event) {
    if (activePointers.has(event.pointerId)) {
      activePointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    }

    if (activePointers.size === 2) {
      const [first, second] = Array.from(activePointers.values());
      const nextDistance = distanceBetweenPointers(first, second);
      if (pinchDistance !== null) {
        updateZoom((pinchDistance - nextDistance) * 0.01);
      }
      pinchDistance = nextDistance;
      drag.active = false;
      mount.classList.remove('is-dragging');
      return;
    }

    if (drag.active) {
      const dx = event.clientX - drag.lastX;
      const dy = event.clientY - drag.lastY;
      drag.lastX = event.clientX;
      drag.lastY = event.clientY;
      drag.rotationY += dx * 0.008;
      drag.rotationX += dy * 0.006;
      drag.rotationX = clamp(drag.rotationX, -0.65, 0.65);
      return;
    }
    const rect = mount.getBoundingClientRect();
    pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    pointer.y = -(((event.clientY - rect.top) / rect.height) * 2 - 1);
  }

  function onPointerDown(event) {
    activePointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (activePointers.size === 2) {
      const [first, second] = Array.from(activePointers.values());
      pinchDistance = distanceBetweenPointers(first, second);
      drag.active = false;
      mount.classList.remove('is-dragging');
      mount.setPointerCapture?.(event.pointerId);
      event.preventDefault();
      return;
    }
    drag.active = true;
    drag.lastX = event.clientX;
    drag.lastY = event.clientY;
    mount.classList.add('is-dragging');
    mount.setPointerCapture?.(event.pointerId);
    event.preventDefault();
  }

  function onPointerUp(event) {
    activePointers.delete(event.pointerId);
    if (activePointers.size < 2) pinchDistance = null;
    drag.active = false;
    mount.classList.remove('is-dragging');
    mount.releasePointerCapture?.(event.pointerId);
  }

  function onWheel(event) {
    event.preventDefault();
    updateZoom(event.deltaY * 0.004);
  }

  mount.addEventListener('pointerdown', onPointerDown);
  mount.addEventListener('pointermove', onPointerMove);
  mount.addEventListener('pointerup', onPointerUp);
  mount.addEventListener('pointercancel', onPointerUp);
  mount.addEventListener('wheel', onWheel, { passive: false });
  mount.addEventListener('pointerleave', function () {
    if (!drag.active) {
      pointer.x = 0;
      pointer.y = 0;
    }
  });
  window.addEventListener('pointerup', function () {
    if (!drag.active) return;
    drag.active = false;
    mount.classList.remove('is-dragging');
  });
  mount.addEventListener('dragstart', function (event) {
    event.preventDefault();
  });
  mount.addEventListener('pointerleave', function () {
    if (drag.active) return;
    pointer.x = 0;
    pointer.y = 0;
  });

  function resize() {
    if (!mount.clientWidth || !mount.clientHeight) return;
    camera.aspect = mount.clientWidth / mount.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(mount.clientWidth, mount.clientHeight);
  }
  window.addEventListener('resize', resize);

  const clock = new THREE.Clock();
  function animate() {
    const elapsed = clock.getElapsedTime();
    earth.rotation.y += prefersReducedMotion ? 0.0012 : 0.0022;
    clouds.rotation.y += prefersReducedMotion ? 0.0016 : 0.0026;
    stars.rotation.y = elapsed * 0.01;
    zoom.current += (zoom.target - zoom.current) * 0.12;
    camera.position.z = zoom.current;

    const targetRotationX = drag.rotationX + pointer.y * 0.18;
    const targetRotationY = drag.rotationY + pointer.x * 0.24;
    earthGroup.rotation.x += (targetRotationX - earthGroup.rotation.x) * 0.08;
    earthGroup.rotation.y += (targetRotationY - earthGroup.rotation.y) * 0.08;
    earthGroup.position.y = Math.sin(elapsed * 0.7) * 0.08;

    renderer.render(scene, camera);
    rafId = requestAnimationFrame(animate);
  }

  resize();
  animate();

  window.addEventListener('beforeunload', function () {
    if (rafId) cancelAnimationFrame(rafId);
    renderer.dispose();
    starsGeometry.dispose();
    earth.geometry.dispose();
    earth.material.dispose();
    clouds.geometry.dispose();
    clouds.material.dispose();
    atmosphere.geometry.dispose();
    atmosphere.material.dispose();
    earthTexture.dispose();
    bumpTexture.dispose();
    nightTexture.dispose();
    landOceanMask.dispose();
    cloudTexture.dispose();
  });
})();
