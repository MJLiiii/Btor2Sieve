(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x62 (bvuge s_7 (_ bv1 8))))
(not $x62)))
(check-sat)
