(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_9 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x205 (bvule i_9 (_ bv127 8))))
(not $x205)))
(check-sat)
