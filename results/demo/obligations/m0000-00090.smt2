(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_5 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x29 (bvuge s_5 (_ bv1 8))))
(not $x29)))
(check-sat)
