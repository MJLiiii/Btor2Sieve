(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_3 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x71 (bvuge s_3 (_ bv1 4))))
(not $x71)))
(check-sat)
