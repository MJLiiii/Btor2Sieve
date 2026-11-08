(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x1371 (bvule s_7 (_ bv127 8))))
(not $x1371)))
(check-sat)
