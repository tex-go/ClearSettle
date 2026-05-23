import { useState, useEffect } from 'react'

var breakpoints = {
  sm:  480,
  md:  768,
  lg:  1024,
  xl:  1280,
  xxl: 1440,
}

function getState(w) {
  return {
    width:     w,
    isMobile:  w < breakpoints.md,
    isTablet:  w >= breakpoints.md && w < breakpoints.lg,
    isDesktop: w >= breakpoints.lg,
    isXs:      w < breakpoints.sm,
    isSm:      w >= breakpoints.sm && w < breakpoints.md,
    isLg:      w >= breakpoints.lg && w < breakpoints.xl,
    isXl:      w >= breakpoints.xl && w < breakpoints.xxl,
    is2xl:     w >= breakpoints.xxl,
  }
}

export default function useBreakpoint() {
  var [state, setState] = useState(function() {
    return getState(typeof window !== 'undefined' ? window.innerWidth : 1024)
  })

  useEffect(function() {
    var raf = null
    function onResize() {
      clearTimeout(raf)
      raf = setTimeout(function() { setState(getState(window.innerWidth)) }, 80)
    }
    window.addEventListener('resize', onResize, { passive: true })
    return function() {
      window.removeEventListener('resize', onResize)
      clearTimeout(raf)
    }
  }, [])

  return state
}
