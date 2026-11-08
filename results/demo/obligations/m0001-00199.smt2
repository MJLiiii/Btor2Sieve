(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_9 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x184 (bvule i_9 (_ bv1 8))))
(not $x184)))
(check-sat)
