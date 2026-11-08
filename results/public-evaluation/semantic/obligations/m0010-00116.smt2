(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_6 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x803 (bvule i_6 (_ bv127 8))))
(not $x803)))
(check-sat)
