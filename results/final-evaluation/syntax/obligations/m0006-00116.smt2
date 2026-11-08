(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_3 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x2944 (bvule s_3 (_ bv1 4))))
(not $x2944)))
(check-sat)
