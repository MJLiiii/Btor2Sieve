(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x1098 (bvule i_7 (_ bv127 8))))
(not $x1098)))
(check-sat)
