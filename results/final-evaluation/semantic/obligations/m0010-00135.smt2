(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x2886 (bvule i_7 (_ bv127 8))))
(not $x2886)))
(check-sat)
